package main

import (
	"os"

	"github.com/stevelandeyasleep/automate-terminal/internal/cli"
)

// Set at build time with -ldflags.
var version = "dev"

func main() {
	os.Exit(cli.Run(os.Args[1:], version))
}
