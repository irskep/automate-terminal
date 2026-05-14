package cli

import (
	"encoding/json"
	"fmt"
	"os"
)

// Output writes to stdout in the requested format.
func Output(format string, data any, text string) {
	switch format {
	case "json":
		enc := json.NewEncoder(os.Stdout)
		enc.SetIndent("", "  ")
		enc.Encode(data)
	case "text":
		fmt.Println(text)
	case "none":
		// silent
	}
}

// OutputError writes an error to stderr in the requested format.
func OutputError(format string, message string, extra map[string]any) {
	switch format {
	case "json":
		data := map[string]any{"success": false, "error": message}
		for k, v := range extra {
			data[k] = v
		}
		enc := json.NewEncoder(os.Stderr)
		enc.SetIndent("", "  ")
		enc.Encode(data)
	case "text", "none":
		fmt.Fprintf(os.Stderr, "Error: %s\n", message)
	}
}
