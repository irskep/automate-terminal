package main

import (
	"fmt"
	"os"

	"github.com/stevelandeyasleep/automate-terminal/internal/cli"
)

// Set at build time with -ldflags.
var version = "dev"

func main() {
	os.Exit(cli.Run(os.Args[1:], version))
}

func init() {
	// Suppress the default log prefix; cli.Run configures logging.
	_ = fmt.Sprintf // avoid unused import during stub phase
}
