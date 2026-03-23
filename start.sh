#!/bin/bash

# FastAPI Application Start Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting FastAPI Application...${NC}"

# Check for config.ini file
if [ ! -f config.ini ]; then
    echo -e "${RED}Error: config.ini file not found!${NC}"
    echo -e "${YELLOW}Please create config.ini from config.ini.example${NC}"
    exit 1
fi
echo -e "${GREEN}Configuration file found.${NC}"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
echo -e "${GREEN}Installing dependencies...${NC}"
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Run database migrations
if [ -d "alembic" ]; then
    echo -e "${GREEN}Running database migrations...${NC}"
    alembic upgrade head
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Start the application
# Configuration is read from config.ini automatically
echo -e "${GREEN}Starting application...${NC}"
exec python src/main.py

