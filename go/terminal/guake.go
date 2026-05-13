package terminal

import (
	"log/slog"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"

	runner "github.com/irskep/automate-terminal/exec"
)

const (
	guakeDBusDest      = "org.guake3.RemoteControl"
	guakeDBusPath      = "/org/guake3/RemoteControl"
	guakeDBusInterface = "org.guake3.RemoteControl"
)

var shellProcessNames = map[string]bool{
	"bash": true, "zsh": true, "fish": true, "sh": true, "dash": true,
}

// Guake implements Terminal for the Guake dropdown terminal on Linux.
type Guake struct {
	Base
	Runner *runner.Runner
	// ProcRoot is the path to /proc. Overridable for testing.
	ProcRoot string
}

func (g *Guake) procRoot() string {
	if g.ProcRoot != "" {
		return g.ProcRoot
	}
	return "/proc"
}

func (g *Guake) DisplayName() string { return "Guake" }

func (g *Guake) Detect(termProgram string) bool {
	if os.Getenv("GUAKE_TAB_UUID") == "" {
		return false
	}
	_, err := exec.LookPath("gdbus")
	return err == nil
}

func (g *Guake) GetCurrentSessionID() *string {
	uuid := os.Getenv("GUAKE_TAB_UUID")
	if uuid == "" {
		return nil
	}
	return &uuid
}

func (g *Guake) GetCapabilities() Capabilities {
	return Capabilities{
		CanCreateTabs:             true,
		CanCreateWindows:          false,
		CanListSessions:           true,
		CanSwitchToSession:        true,
		CanDetectSessionID:        true,
		CanDetectWorkingDirectory: true,
		CanPasteCommands:          true,
		CanRunInActiveSession:     true,
	}
}

func (g *Guake) SessionExists(sessionID string) bool {
	if sessionID == "" {
		return false
	}
	for _, s := range g.getShellProcesses() {
		if s.tabUUID == sessionID {
			return true
		}
	}
	return false
}

func (g *Guake) SwitchToSession(sessionID string, pasteScript *string) bool {
	idx := g.callGDBusInt("get_index_from_uuid", sessionID)
	if idx == nil || *idx < 0 {
		slog.Error("Tab not found", "uuid", sessionID)
		return false
	}
	if _, ok := g.callGDBus("select_tab", strconv.Itoa(*idx)); !ok {
		return false
	}
	if g.callGDBusBool("get_visibility") == boolFalse {
		if _, ok := g.callGDBus("show"); !ok {
			return false
		}
	}
	if pasteScript != nil {
		_, ok := g.callGDBus("execute_command", *pasteScript+"\n")
		return ok
	}
	return true
}

func (g *Guake) OpenNewTab(dir string, pasteScript *string) bool {
	if _, ok := g.callGDBus("add_tab", dir); !ok {
		return false
	}
	if g.callGDBusBool("get_visibility") == boolFalse {
		if _, ok := g.callGDBus("show"); !ok {
			return false
		}
	}
	if pasteScript != nil {
		_, ok := g.callGDBus("execute_command", *pasteScript+"\n")
		return ok
	}
	return true
}

func (g *Guake) OpenNewWindow(dir string, pasteScript *string) bool {
	// Guake is a dropdown terminal; it doesn't support multiple windows.
	slog.Debug("Guake doesn't support windows, creating tab instead")
	return g.OpenNewTab(dir, pasteScript)
}

func (g *Guake) ListSessions() []Session {
	procs := g.getShellProcesses()
	seen := make(map[string]bool)
	var sessions []Session
	for _, p := range procs {
		if seen[p.tabUUID] {
			continue
		}
		seen[p.tabUUID] = true
		sessions = append(sessions, Session{
			SessionID:        p.tabUUID,
			WorkingDirectory: p.cwd,
		})
	}
	return sessions
}

func (g *Guake) FindSessionByWorkingDirectory(target string, subdirectoryOK bool) *string {
	return findSessionByDir(g.ListSessions(), target, subdirectoryOK)
}

func (g *Guake) RunInActiveSession(command string) bool {
	_, ok := g.callGDBus("execute_command", command+"\n")
	return ok
}

// gdbus helpers

func (g *Guake) callGDBus(method string, args ...string) (string, bool) {
	cmd := []string{
		"gdbus", "call", "--session",
		"--dest", guakeDBusDest,
		"--object-path", guakeDBusPath,
		"--method", guakeDBusInterface + "." + method,
	}
	cmd = append(cmd, args...)
	output, ok := g.Runner.ExecuteRWithOutput(cmd)
	return output, ok
}

type tribool int

const (
	boolUnknown tribool = iota
	boolTrue
	boolFalse
)

func (g *Guake) callGDBusBool(method string, args ...string) tribool {
	output, ok := g.callGDBus(method, args...)
	if !ok {
		return boolUnknown
	}
	lower := strings.ToLower(output)
	if strings.Contains(lower, "true") || strings.Contains(lower, "(1,") {
		return boolTrue
	}
	if strings.Contains(lower, "false") || strings.Contains(lower, "(0,") {
		return boolFalse
	}
	return boolUnknown
}

var gdbusIntRe = regexp.MustCompile(`-?\d+`)

func (g *Guake) callGDBusInt(method string, args ...string) *int {
	output, ok := g.callGDBus(method, args...)
	if !ok {
		return nil
	}
	m := gdbusIntRe.FindString(output)
	if m == "" {
		return nil
	}
	v, err := strconv.Atoi(m)
	if err != nil {
		return nil
	}
	return &v
}

// /proc-based session discovery

type guakeProc struct {
	tabUUID string
	cwd     string
	pid     int
}

type procInfo struct {
	name string
	ppid int
	path string
}

func (g *Guake) getShellProcesses() []guakeProc {
	root := g.procRoot()
	entries, err := os.ReadDir(root)
	if err != nil {
		slog.Error("Failed to read proc root", "path", root, "err", err)
		return nil
	}

	processes := make(map[int]procInfo)
	guakePIDs := make(map[int]bool)

	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}
		pid, err := strconv.Atoi(entry.Name())
		if err != nil {
			continue
		}
		procPath := filepath.Join(root, entry.Name())
		name := readProcComm(procPath)
		if name == "" {
			continue
		}
		ppid := readProcPPid(procPath)
		processes[pid] = procInfo{name: name, ppid: ppid, path: procPath}
		if strings.Contains(strings.ToLower(name), "guake") {
			guakePIDs[pid] = true
		}
	}

	if len(guakePIDs) == 0 {
		return nil
	}

	var result []guakeProc
	for pid, info := range processes {
		if !shellProcessNames[info.name] {
			continue
		}
		if !hasGuakeAncestor(pid, processes, guakePIDs) {
			continue
		}
		env := readProcEnviron(info.path)
		tabUUID := env["GUAKE_TAB_UUID"]
		if tabUUID == "" {
			continue
		}
		cwd := readProcCwd(info.path)
		if cwd == "" {
			continue
		}
		result = append(result, guakeProc{tabUUID: tabUUID, cwd: cwd, pid: pid})
	}
	return result
}

func hasGuakeAncestor(pid int, procs map[int]procInfo, guakePIDs map[int]bool) bool {
	visited := make(map[int]bool)
	current := pid
	for {
		info, ok := procs[current]
		if !ok || info.ppid <= 1 {
			return false
		}
		if guakePIDs[info.ppid] {
			return true
		}
		if visited[info.ppid] {
			return false
		}
		visited[info.ppid] = true
		current = info.ppid
	}
}

func readProcComm(procPath string) string {
	data, err := os.ReadFile(filepath.Join(procPath, "comm"))
	if err != nil {
		return ""
	}
	return strings.TrimSpace(string(data))
}

func readProcPPid(procPath string) int {
	data, err := os.ReadFile(filepath.Join(procPath, "status"))
	if err != nil {
		return 0
	}
	for _, line := range strings.Split(string(data), "\n") {
		if strings.HasPrefix(line, "PPid:") {
			fields := strings.Fields(line)
			if len(fields) >= 2 {
				v, _ := strconv.Atoi(fields[1])
				return v
			}
		}
	}
	return 0
}

func readProcEnviron(procPath string) map[string]string {
	data, err := os.ReadFile(filepath.Join(procPath, "environ"))
	if err != nil {
		return nil
	}
	env := make(map[string]string)
	for _, entry := range strings.Split(string(data), "\x00") {
		if entry == "" {
			continue
		}
		parts := strings.SplitN(entry, "=", 2)
		if len(parts) == 2 {
			env[parts[0]] = parts[1]
		}
	}
	return env
}

func readProcCwd(procPath string) string {
	target, err := os.Readlink(filepath.Join(procPath, "cwd"))
	if err != nil {
		return ""
	}
	return target
}

var _ Terminal = (*Guake)(nil)
