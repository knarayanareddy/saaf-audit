#!/bin/sh
claude -p "audit the checked out repo" --permission-mode default --allowedTools "Read,Grep,Glob"
