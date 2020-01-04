#!/bin/bash

if ! command -v python3 &>/dev/null; then
    echo 'Installing python3'
    sudo apt-get install python3
fi

if ! command -v pip3 &>/dev/null; then
    echo 'Installing pip'
    sudo apt-get install python3-pip
fi

if ! command -v mongo &>/dev/null; then
    echo 'Installing mongodb'
    sudo apt-get install mongodb
fi

pip3 install -r requirements.txt
