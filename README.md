# UniFi PoE Control Script

A Python script that uses the `aiounifi` library to set Power over Ethernet (PoE) status on specified ports of a UniFi switch to a desired state through the UniFi Network Controller.

## Features

- **Set PoE Status**: Set PoE on/off for individual ports or ranges of ports to a specific desired state
- **State-Based Control**: Specify exactly what state you want (on/off, enable/disable)
  - `--state on` or `--state enable` → enables PoE (sets to 'auto' mode)
  - `--state off` or `--state disable` → disables PoE (sets to 'off' mode)
- **Flexible Port Selection**: Support for individual ports, ranges, and comma-separated lists
- **Automation Ready**: Optional `--yes` flag to skip confirmations for scripts and CI/CD
- **Safety Features**:
  - User confirmation before making changes (can be bypassed with `--yes`)
  - Verification of changes after execution
  - Checks for PoE capability on each port
- **Comprehensive Logging**: Detailed logging with configurable levels
- **Error Handling**: Robust error handling with informative messages

## Prerequisites

- Python 3.8 or later
- UniFi Network Controller (tested with 7.x and 8.x)
- Network access to the UniFi controller
- Valid credentials for the UniFi controller
- UniFi switch with PoE capability

## Installation

1. **Clone or download this repository**

2. **Install dependencies** (if not using the existing virtual environment):

   ```bash
   pip install -r requirements.txt
   ```

3. **Or use the existing virtual environment**:
   ```bash
   source venv/bin/activate  # On Linux/Mac
   # or
   venv\Scripts\activate     # On Windows
   ```

## Usage

### Basic Syntax

```bash
python unifi_poe_toggle.py <controller_host> <username> <password> <switch_mac> <port_indexes> --state <on|off> [options]
```

### Arguments

- `controller_host`: IP address or hostname of your UniFi controller
- `username`: Username for UniFi controller login
- `password`: Password for UniFi controller login
- `switch_mac`: MAC address of the target switch (any format: `aa:bb:cc:dd:ee:ff`, `aa-bb-cc-dd-ee-ff`, or `aabbccddeeff`)
- `port_indexes`: Port numbers to configure (see examples below for formats)

### Required Options

- `--state {on,off,enable,disable}`: Desired PoE state (on/enable to turn on, off/disable to turn off)

### Additional Options

- `--port PORT`: Controller port (default: 443)
- `--site SITE`: Site name (default: "default")
- `--verify-ssl`: Verify SSL certificates (default: disabled for self-signed certs)
- `--yes`: Skip confirmation prompt (for automation)
- `--debug`: Enable debug logging
- `--help`: Show help message

### Port Index Formats

The script supports flexible port specification:

- **Individual ports**: `1,3,5,8`
- **Ranges**: `1-8` (ports 1 through 8)
- **Mixed**: `1,3,5-8,12` (ports 1, 3, 5, 6, 7, 8, and 12)

## Examples

### Basic Usage - Enable PoE

Enable PoE on ports 1, 2, and 3:

```bash
python unifi_poe_toggle.py 192.168.1.1 admin mypassword 00:11:22:33:44:55 1,2,3 --state on
```

### Basic Usage - Disable PoE

Disable PoE on ports 1, 2, and 3:

```bash
python unifi_poe_toggle.py 192.168.1.1 admin mypassword 00:11:22:33:44:55 1,2,3 --state off
```

### Range of Ports

Enable PoE on ports 1 through 8:

```bash
python unifi_poe_toggle.py 192.168.1.1 admin mypassword 00:11:22:33:44:55 1-8 --state enable
```

### Custom Controller Port

For a controller on a non-standard port (like UniFi OS on port 443):

```bash
python unifi_poe_toggle.py 192.168.1.1 admin mypassword 00:11:22:33:44:55 5,10-12 --state off --port 443
```

### Multiple Sites

For a specific site (not the default):

```bash
python unifi_poe_toggle.py unifi.local admin mypassword aa:bb:cc:dd:ee:ff 1-24 --state on --site branch-office
```

### Debug Mode

Enable detailed logging for troubleshooting:

```bash
python unifi_poe_toggle.py 192.168.1.1 admin mypassword 00:11:22:33:44:55 1,2,3 --state on --debug
```

### Automation Mode

Skip confirmation prompts for scripting and automation:

```bash
# For scripts and automation - no user interaction required
python unifi_poe_toggle.py 192.168.1.1 admin mypassword 00:11:22:33:44:55 1,2,3 --state off --yes

# Can be combined with other options
python unifi_poe_toggle.py 10.101.1.1 api-user mypass 28:70:4e:ed:e6:22 1-8 --state on --port 443 --yes
```

## How It Works

1. **Connection**: Connects to the UniFi controller using the provided credentials
2. **Device Discovery**: Finds the specified switch by MAC address
3. **Status Check**: Reads current PoE status for the specified ports
4. **State Analysis**: Compares current state with desired state for each port:
   - If already in desired state → skip (no change needed)
   - If different from desired state → plan configuration change
5. **User Confirmation**: Shows planned changes and asks for confirmation
6. **Execution**: Sends PoE configuration changes to the controller
7. **Verification**: Checks that changes were applied successfully

## PoE Modes

The script works with these UniFi PoE modes:

- **`off`**: PoE disabled
- **`auto`**: Automatic PoE (PoE/PoE+/PoE++ as needed)
- **`24v`**: 24V passive PoE
- **`passthrough`**: PoE passthrough mode

When setting PoE states:

- `--state on` or `--state enable` → sets port to "auto" (enable PoE with automatic detection)
- `--state off` or `--state disable` → sets port to "off" (disable PoE)

## Sample Output

```
2024-01-15 10:30:15,123 - INFO - Target ports: [1, 2, 3, 8]
2024-01-15 10:30:15,124 - INFO - Connecting to UniFi controller at 192.168.1.1:8443
2024-01-15 10:30:16,234 - INFO - Successfully connected to UniFi controller
2024-01-15 10:30:16,235 - INFO - Looking for switch with MAC: 00:11:22:33:44:55
2024-01-15 10:30:16,456 - INFO - Found switch: Main Switch (USW-24-PoE)
2024-01-15 10:30:16,457 - INFO - Current PoE status for 4 ports:
2024-01-15 10:30:16,457 - INFO -   Port 1 (Camera Port): off
2024-01-15 10:30:16,458 - INFO -   Port 2 (AP Port): auto
2024-01-15 10:30:16,458 - INFO -   Port 3 (Phone Port): off
2024-01-15 10:30:16,459 - INFO -   Port 8 (Server Port): auto
2024-01-15 10:30:16,457 - INFO - Port 1 (Camera Port) is already off (off)
2024-01-15 10:30:16,458 - INFO - Will enable PoE on port 2 (AP Port): auto -> off
2024-01-15 10:30:16,458 - INFO - Port 3 (Phone Port) is already off (off)
2024-01-15 10:30:16,459 - INFO - Will disable PoE on port 8 (Server Port): auto -> off

About to disable PoE on 2 ports:
  - Disable PoE on port 2 (AP Port)
  - Disable PoE on port 8 (Server Port)

Proceed? (y/N): y
2024-01-15 10:30:20,123 - INFO - Sending PoE configuration request for 2 ports...
2024-01-15 10:30:20,789 - INFO - PoE configuration request completed successfully
2024-01-15 10:30:20,790 - INFO - Verifying PoE configuration changes...
2024-01-15 10:30:23,457 - INFO - ✓ Port 2 (AP Port): PoE disabled successfully (off)
2024-01-15 10:30:23,459 - INFO - ✓ Port 8 (Server Port): PoE disabled successfully (off)
2024-01-15 10:30:23,460 - INFO - PoE configuration operation completed
```

## Troubleshooting

### Common Issues

1. **Connection Failed**

   - Verify controller IP/hostname and port
   - Check network connectivity
   - Ensure controller is accessible

2. **Login Failed**

   - Verify username and password
   - Check if account has sufficient permissions
   - Ensure account is not locked

3. **Switch Not Found**

   - Verify the MAC address format and value
   - Ensure the switch is adopted and online
   - Check if you're connecting to the correct site

4. **Port Not Found**

   - Verify port numbers exist on the switch
   - Check if ports are within valid range for the switch model

5. **PoE Not Supported**
   - Verify the switch supports PoE
   - Check if specific ports have PoE capability
   - Some ports may not support PoE even on PoE switches

### Debug Mode

Use `--debug` flag for detailed troubleshooting information:

```bash
python unifi_poe_toggle.py 192.168.1.1 admin password 00:11:22:33:44:55 1,2,3 --debug
```

This will show:

- Detailed connection information
- API request/response data
- Switch and port discovery details
- Raw device information

### SSL Certificate Issues

If you encounter SSL certificate errors with self-signed certificates:

```bash
# Disable SSL verification (default behavior)
python unifi_poe_toggle.py 192.168.1.1 admin password 00:11:22:33:44:55 1,2,3

# Or explicitly disable with older versions
python unifi_poe_toggle.py 192.168.1.1 admin password 00:11:22:33:44:55 1,2,3 --no-verify-ssl
```

## Security Considerations

- **Credentials**: Avoid hardcoding credentials in scripts. Consider using environment variables or configuration files with appropriate permissions.
- **Network**: Use this script only on trusted networks.
- **SSL**: Enable SSL verification (`--verify-ssl`) when using properly signed certificates.
- **Permissions**: The UniFi user account needs appropriate permissions to modify device settings.

## Limitations

- **PoE Only**: This script only controls PoE settings, not other port configurations
- **Single Switch**: Targets one switch at a time (though multiple ports)
- **Network Controller**: Requires UniFi Network Controller (not suitable for standalone switches)
- **Authentication**: Currently supports username/password authentication only

## License

This script is provided as-is for educational and operational purposes. Use responsibly and test in non-production environments first.

## Contributing

Feel free to submit issues and enhancement requests! When contributing:

1. Test your changes thoroughly
2. Update documentation as needed
3. Follow existing code style
4. Add appropriate error handling
