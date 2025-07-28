-- This script will make user_agent and device_fp columns nullable in RCI_device_nicknames
ALTER TABLE RCI_device_nicknames ALTER COLUMN user_agent NVARCHAR(256) NULL;
ALTER TABLE RCI_device_nicknames ALTER COLUMN device_fp NVARCHAR(256) NULL;
