#!/usr/bin/env python3
"""
UniFi PoE Control Script

This script uses the aiounifi library to set Power over Ethernet (PoE) 
status on specified ports of a UniFi switch to a desired state.

Usage:
    python unifi_poe_control.py <controller_host> <username> <password> <switch_mac> <port_indexes> --state <on|off>

Examples:
    python unifi_poe_control.py 192.168.1.1 admin password 00:11:22:33:44:55 1,2,3,8 --state on
    python unifi_poe_control.py 192.168.1.1 admin password 00:11:22:33:44:55 1,2,3,8 --state off
"""

import argparse
import asyncio
import logging
import sys
from typing import List

import aiohttp
import aiounifi
from aiounifi.controller import Controller
from aiounifi.models.configuration import Configuration
from aiounifi.models.device import DeviceSetPoePortModeRequest

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def connect_to_controller(
    host: str,
    username: str,
    password: str,
    port: int = 443,
    site: str = "default",
    verify_ssl: bool = False
) -> Controller:
    """Connect to UniFi controller and return Controller instance."""
    logger.info(f"Connecting to UniFi controller at {host}:{port}")
    
    session = aiohttp.ClientSession(
        cookie_jar=aiohttp.CookieJar(unsafe=True),
        connector=aiohttp.TCPConnector(ssl=verify_ssl)
    )
    
    controller = Controller(
        Configuration(
            session,
            host,
            username=username,
            password=password,
            port=port,
            site=site,
            ssl_context=verify_ssl
        )
    )
    
    try:
        await controller.login()
        logger.info("Successfully connected to UniFi controller")
        return controller
    except aiounifi.LoginRequired:
        logger.error("Login failed - check username and password")
        raise
    except aiounifi.Unauthorized:
        logger.error("Unauthorized - check credentials")
        raise
    except Exception as e:
        logger.error(f"Failed to connect to controller: {e}")
        raise


async def find_switch_by_mac(controller: Controller, switch_mac: str):
    """Find switch device by MAC address."""
    logger.info(f"Looking for switch with MAC: {switch_mac}")
    
    # Update devices to get latest information
    await controller.devices.update()
    
    # Normalize MAC address format (remove separators and convert to lowercase)
    normalized_target_mac = switch_mac.replace(":", "").replace("-", "").lower()
    
    for device in controller.devices.values():
        device_mac = device.mac.replace(":", "").replace("-", "").lower()
        if device_mac == normalized_target_mac:
            logger.info(f"Found switch: {device.name} ({device.model})")
            return device
    
    raise ValueError(f"Switch with MAC {switch_mac} not found")


def get_current_poe_status(device, port_indexes: List[int]) -> dict:
    """Get current PoE status for specified ports."""
    port_status = {}
    
    if not hasattr(device, 'port_table') or not device.port_table:
        raise ValueError("Device does not have port table (not a switch?)")
    
    for port in device.port_table:
        port_idx = port.get('port_idx')
        if port_idx in port_indexes:
            poe_mode = port.get('poe_mode', 'unknown')
            poe_enable = port.get('poe_enable', False)
            port_name = port.get('name', f"Port {port_idx}")
            
            port_status[port_idx] = {
                'name': port_name,
                'current_mode': poe_mode,
                'poe_enable': poe_enable,
                'poe_caps': port.get('poe_caps', 0)
            }
    
    return port_status


def determine_set_actions(port_status: dict, desired_state: str) -> List[tuple]:
    """Determine what PoE mode to set for each port to achieve the desired state."""
    actions = []
    
    # Map desired state to PoE mode and action description
    if desired_state.lower() in ['on', 'enable', 'enabled', 'true', '1']:
        target_mode = 'auto'
        action_desc = "enable"
        target_state = 'on'
    elif desired_state.lower() in ['off', 'disable', 'disabled', 'false', '0']:
        target_mode = 'off'
        action_desc = "disable"
        target_state = 'off'
    else:
        raise ValueError(f"Invalid desired state: {desired_state}. Use 'on' or 'off'")
    
    for port_idx, status in port_status.items():
        current_mode = status['current_mode']
        poe_caps = status['poe_caps']
        
        # Check if port supports PoE
        if poe_caps == 0:
            logger.warning(f"Port {port_idx} ({status['name']}) does not support PoE")
            continue
        
        # Check if port is already in desired state
        current_state = 'off' if current_mode == 'off' else 'on'
        
        if current_state == target_state:
            logger.info(f"Port {port_idx} ({status['name']}) is already {target_state} ({current_mode})")
            continue
        
        # Add action to change port to desired state
        actions.append((port_idx, target_mode, action_desc))
        logger.info(f"Will {action_desc} PoE on port {port_idx} ({status['name']}): {current_mode} -> {target_mode}")
    
    return actions


async def set_poe_ports(controller: Controller, device, actions: List[tuple]) -> bool:
    """Set PoE on the specified ports to the desired state."""
    if not actions:
        logger.info("No PoE changes needed - all ports are already in the desired state")
        return True
    
    try:
        # Create the request to set PoE modes
        targets = [(port_idx, mode) for port_idx, mode, _ in actions]
        request = DeviceSetPoePortModeRequest.create(device, targets=targets)
        
        logger.info(f"Sending PoE configuration request for {len(actions)} ports...")
        response = await controller.request(request)
        
        if response.get('meta', {}).get('rc') == 'ok':
            logger.info("PoE configuration request completed successfully")
            return True
        else:
            logger.error(f"PoE configuration request failed: {response}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to set PoE: {e}")
        return False


async def verify_changes(controller: Controller, device, original_status: dict, actions: List[tuple]):
    """Verify that PoE configuration changes were applied successfully."""
    logger.info("Verifying PoE configuration changes...")
    
    # Wait a moment for changes to propagate
    await asyncio.sleep(2)
    
    # Refresh device information
    await controller.devices.update()
    
    # Get updated switch device
    updated_device = None
    for dev in controller.devices.values():
        if dev.mac == device.mac:
            updated_device = dev
            break
    
    if not updated_device:
        logger.error("Could not find updated device information")
        return
    
    # Check each port that was modified
    action_dict = {port_idx: (new_mode, action) for port_idx, new_mode, action in actions}
    
    for port in updated_device.port_table:
        port_idx = port.get('port_idx')
        if port_idx in action_dict:
            current_mode = port.get('poe_mode', 'unknown')
            expected_mode, action = action_dict[port_idx]
            port_name = port.get('name', f"Port {port_idx}")
            
            if current_mode == expected_mode:
                logger.info(f"✓ Port {port_idx} ({port_name}): PoE {action}d successfully ({current_mode})")
            else:
                logger.warning(f"⚠ Port {port_idx} ({port_name}): Expected {expected_mode}, got {current_mode}")


async def main(host: str, username: str, password: str, switch_mac: str, 
               port_indexes: List[int], desired_state: str, port: int = 8443, 
               site: str = "default", verify_ssl: bool = False, yes: bool = False):
    """Main function to set PoE on specified switch ports to desired state."""
    controller = None
    session = None
    try:
        # Connect to controller
        controller = await connect_to_controller(host, username, password, port, site, verify_ssl)
        session = controller.connectivity.config.session
        
        # Find the switch
        device = await find_switch_by_mac(controller, switch_mac)
        
        # Get current PoE status
        current_status = get_current_poe_status(device, port_indexes)
        
        if not current_status:
            logger.error("No valid ports found with the specified indexes")
            return False
        
        logger.info(f"Current PoE status for {len(current_status)} ports:")
        for port_idx, status in current_status.items():
            logger.info(f"  Port {port_idx} ({status['name']}): {status['current_mode']}")
        
        # Determine actions needed to reach desired state
        actions = determine_set_actions(current_status, desired_state)
        
        if not actions:
            logger.info(f"All specified ports are already in the desired state ({desired_state})")
            return True
        
        # Confirm actions with user (unless --yes flag is used)
        state_desc = "enable" if desired_state.lower() in ['on', 'enable', 'enabled', 'true', '1'] else "disable"
        print(f"\nAbout to {state_desc} PoE on {len(actions)} ports:")
        for port_idx, new_mode, action in actions:
            port_name = current_status[port_idx]['name']
            print(f"  - {action.capitalize()} PoE on port {port_idx} ({port_name})")
        
        if not yes:
            response = input("\nProceed? (y/N): ").strip().lower()
            if response != 'y':
                logger.info("Operation cancelled by user")
                return False
        else:
            print("\nProceeding automatically with --yes flag...")
            logger.info("Proceeding without confirmation due to --yes flag")
        
        # Set PoE to desired state
        success = await set_poe_ports(controller, device, actions)
        
        if success:
            # Verify changes
            await verify_changes(controller, device, current_status, actions)
            logger.info("PoE configuration operation completed")
            return True
        else:
            logger.error("PoE configuration operation failed")
            return False
            
    except Exception as e:
        logger.error(f"Error during PoE configuration operation: {e}")
        return False
    finally:
        if session:
            await session.close()


def parse_port_indexes(port_string: str) -> List[int]:
    """Parse comma-separated port indexes into a list of integers."""
    try:
        ports = []
        for part in port_string.split(','):
            part = part.strip()
            if '-' in part:
                # Handle ranges like "1-4"
                start, end = map(int, part.split('-'))
                ports.extend(range(start, end + 1))
            else:
                # Handle individual ports
                ports.append(int(part))
        return sorted(list(set(ports)))  # Remove duplicates and sort
    except ValueError as e:
        raise ValueError(f"Invalid port specification '{port_string}': {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Set PoE status on UniFi switch ports to desired state",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s 192.168.1.1 admin password 00:11:22:33:44:55 1,2,3 --state on
  %(prog)s 192.168.1.1 admin password 00:11:22:33:44:55 1-8 --state off --port 443
  %(prog)s unifi.local admin password aa:bb:cc:dd:ee:ff 5,10-12 --state enable --site main
  %(prog)s 192.168.1.1 admin password 00:11:22:33:44:55 1,2,3 --state off --yes  # For automation
        """
    )
    
    parser.add_argument("host", help="UniFi controller hostname or IP")
    parser.add_argument("username", help="Username for UniFi controller")
    parser.add_argument("password", help="Password for UniFi controller")
    parser.add_argument("switch_mac", help="MAC address of the switch")
    parser.add_argument("ports", help="Port indexes to configure (comma-separated, ranges supported)")
    parser.add_argument("--state", required=True, choices=['on', 'off', 'enable', 'disable'], 
                       help="Desired PoE state (on/enable or off/disable)")
    parser.add_argument("--port", type=int, default=443, help="Controller port (default: 443)")
    parser.add_argument("--site", default="default", help="Site name (default: default)")
    parser.add_argument("--verify-ssl", action="store_true", help="Verify SSL certificates")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompt (for automation)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        port_indexes = parse_port_indexes(args.ports)
        logger.info(f"Target ports: {port_indexes}")
    except ValueError as e:
        logger.error(f"Error parsing port indexes: {e}")
        sys.exit(1)
    
    try:
        success = asyncio.run(main(
            args.host,
            args.username,
            args.password,
            args.switch_mac,
            port_indexes,
            args.state,
            args.port,
            args.site,
            args.verify_ssl,
            args.yes
        ))
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1) 