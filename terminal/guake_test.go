package terminal

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/irskep/automate-terminal/exec"
)

func TestGuakeGetShellProcesses(t *testing.T) {
	procRoot := t.TempDir()

	// Guake process (PID 1000)
	guakeDir := filepath.Join(procRoot, "1000")
	os.Mkdir(guakeDir, 0o755)
	os.WriteFile(filepath.Join(guakeDir, "comm"), []byte("guake\n"), 0o644)
	os.WriteFile(filepath.Join(guakeDir, "status"), []byte("Name:\tguake\nPPid:\t1\n"), 0o644)
	os.WriteFile(filepath.Join(guakeDir, "environ"), []byte{}, 0o644)
	projectDir := filepath.Join(procRoot, "project")
	os.Mkdir(projectDir, 0o755)
	os.Symlink(projectDir, filepath.Join(guakeDir, "cwd"))

	// Shell process under Guake (PID 1001)
	shellDir := filepath.Join(procRoot, "1001")
	os.Mkdir(shellDir, 0o755)
	os.WriteFile(filepath.Join(shellDir, "comm"), []byte("bash\n"), 0o644)
	os.WriteFile(filepath.Join(shellDir, "status"), []byte("Name:\tbash\nPPid:\t1000\n"), 0o644)
	os.WriteFile(filepath.Join(shellDir, "environ"), []byte("GUAKE_TAB_UUID=tab-abc\x00SHELL=/bin/bash\x00"), 0o644)
	targetCwd := filepath.Join(procRoot, "workspace")
	os.Mkdir(targetCwd, 0o755)
	os.Symlink(targetCwd, filepath.Join(shellDir, "cwd"))

	// Unrelated process (PID 2000) -- should be ignored
	otherDir := filepath.Join(procRoot, "2000")
	os.Mkdir(otherDir, 0o755)
	os.WriteFile(filepath.Join(otherDir, "comm"), []byte("python\n"), 0o644)
	os.WriteFile(filepath.Join(otherDir, "status"), []byte("Name:\tpython\nPPid:\t1\n"), 0o644)
	os.WriteFile(filepath.Join(otherDir, "environ"), []byte{}, 0o644)
	os.Symlink(procRoot, filepath.Join(otherDir, "cwd"))

	g := &Guake{Runner: &exec.Runner{}, ProcRoot: procRoot}
	sessions := g.getShellProcesses()

	if len(sessions) != 1 {
		t.Fatalf("expected 1 session, got %d", len(sessions))
	}
	if sessions[0].tabUUID != "tab-abc" {
		t.Errorf("expected tab-abc, got %s", sessions[0].tabUUID)
	}
	if sessions[0].cwd != targetCwd {
		t.Errorf("expected %s, got %s", targetCwd, sessions[0].cwd)
	}
}

func TestGuakeDetect(t *testing.T) {
	origUUID := os.Getenv("GUAKE_TAB_UUID")
	defer os.Setenv("GUAKE_TAB_UUID", origUUID)

	g := &Guake{Runner: &exec.Runner{}}

	os.Unsetenv("GUAKE_TAB_UUID")
	if g.Detect("") {
		t.Error("expected not detected without GUAKE_TAB_UUID")
	}

	os.Setenv("GUAKE_TAB_UUID", "tab-123")
	// Detection also requires gdbus on PATH. We can't guarantee that in tests,
	// so we just verify the env var check.
}
