# File Monitor Project

## Overview

This project monitors specified files and directories for deletions and modifications and restores them if unauthorized changes are detected. It uses Python, PyQt5 for the GUI, and Watchdog for filesystem event monitoring.
Motivation
### Protecting Binary Files

Binary files, such as executables and libraries, are critical components of any system. Unauthorized modifications to these files can lead to serious issues like system instability, data corruption, or security vulnerabilities. Altering binary files is a common method used by viruses and other malware to compromise systems.

To prevent such unauthorized changes, this project implements strict monitoring of binary files. Any modification to a binary file triggers an immediate restoration process unless explicitly approved. This ensures that all changes to critical files are deliberate and authorized, safeguarding the system against potential threats.

### Customizable File Monitoring

In addition to binary files, the project allows monitoring of any file type. Recognizing that different files may require different levels of protection, we provide the ability to set customizable thresholds for what constitutes a "significant" change. By default, the system applies a general threshold, but users can specify their own thresholds for different file extensions (suffixes) based on their specific needs. This flexibility allows users to tailor the monitoring system to suit the unique requirements of their environment.

## Features

- Monitors specified files and directories.
- Restores deleted files and directories.
- Checks for significant changes in files and restores them if unauthorized modifications are detected.
- Password-protected restoration.
- User can set the level of restrictions to solve the ambiguity of the words "significant" or "suspicious" changes.

## How It Works
### Initialization and Configuration

#### Setup:
Upon first running the project, it initializes the necessary directories and configuration files. Users are prompted to select the files and directories they wish to monitor. This selection is saved in a configuration file for future sessions.

#### Password Protection:
The user sets a password that will be used to authorize any restoration actions. This adds a layer of security, ensuring that only authorized users can approve changes to monitored files.

### Monitoring Process

#### Real-Time Monitoring:
The project uses the Watchdog library to monitor the specified files and directories in real-time. It listens for file system events, such as deletions, modifications, or creations.

#### Binary Files:
For binary files (e.g., files with extensions such as .bin, .exe, .dll), the project strictly monitors any changes. Even minor modifications, such as changes in file size, trigger an alert. The user must then approve the change by entering the password, or the file is automatically restored to its last known good state.

#### Text and Other Files:
For non-binary files, the project compares the current version with the previous backup. It calculates the "difference" based on a customizable threshold. If the changes exceed this threshold, the project prompts for approval before allowing the modification.

### Restoration Process

#### Password Verification:
When unauthorized or significant changes are detected, the project pauses and prompts the user to enter the password. If the correct password is provided, the change is allowed. If the password is incorrect or if the user cancels, the project automatically restores the file or directory from its backup.

#### Backup Creation:
Initially, and whenever changes are approved, the project creates a backup of the monitored files. These backups are stored in a secure directory, ensuring that the original state of each file is preserved.

### Customization

#### Thresholds:
Users can customize the sensitivity of the monitoring process by setting thresholds for different file types. For example, you can specify that a .txt file should only trigger a restoration if more than 50 characters are changed, while a .bin file might trigger on any change.

#### Exclusions:
Certain file types (e.g., temporary files such as .swp, .swo, .tmp) are excluded from monitoring to prevent unnecessary alerts and restorations, enhancing the overall user experience.

### User Interface

#### GUI:
The project provides a user-friendly interface using PyQt5, where users can manage their monitored files, set thresholds, and view real-time alerts. The GUI simplifies the process of configuring the system, making it accessible even to users with minimal technical expertise.


## Installation

### Prerequisites

- Python 3
- pip (Python package installer)

### Install Dependencies and Run the Project

Run the provided shell script to install all necessary dependencies and start the file monitor:

```sh
./install_and_run.sh
```


## Conclusion

### Limitations

Password Dependency: The project relies on user-provided passwords for restoration, which could be a single point of failure if the password is lost or compromised.
Performance Impact: Monitoring large directories or a large number of files may impact performance.
Simple Authentication: Only simple password authentication is implemented, which might not be sufficient for more secure applications.

### Advantages

- Real-Time Monitoring: Provides real-time monitoring and restoration of files and directories.

- Customizable Thresholds: Allows for customization of file modification thresholds.

- User-Friendly: Easy to set up and configure with a user-friendly GUI.

- Restriction Levels: Users can set the level of restrictions to define what constitutes "significant" or "suspicious" changes.

- Real-Time Processing: The real-time nature of Qt provides an advantage over frameworks like React.

### Challenges

- Concurrency Management: The hardest part of the project was dealing with concurrency, which was managed by restarting the observer to update after each change.

- Password Protection: Implementing the password-protected restoration mechanism was complex and required careful handling of user input and validation.

- Efficient Restoration: Ensuring the correct and efficient restoration of files and directories while maintaining system performance was challenging.

- GUI Integration: While creating the GUI using PyQt5 was straightforward, integrating it was very hard due to the real-time nature of Qt compared to frameworks like React.

### Easier Tasks

- Watchdog Setup: Setting up Watchdog for filesystem event monitoring was straightforward due to its comprehensive documentation.

- General Flow: The general flow of the application, including the setup of the main monitoring loop and handling file system events, was straightforward to implement thanks to the clear structure provided by Watchdog and PyQt5.

### Cooperation

The project benefited greatly from excellent teamwork and communication. Each team member focused on different aspects of the project, leading to effective and efficient problem-solving and implementation.