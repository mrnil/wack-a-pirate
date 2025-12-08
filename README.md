# wack-a-pirate: Whack-A-Pirate Battle
## Overview
Whack-A-Pirate Battle is a fast-paced, hardware-integrated game built using Pygame that transforms the classic "Whack-A-Mole" mechanic into a frantic defense battle.

The primary objective is to defend your fixed Ship from an invading Enemy Fleet of ships before your Ship health (PLAYER_MAX_HEALTH is 10) drops to zero.

## Core Gameplay
The game runs for a fixed duration of 30 seconds (GAME_DURATION) and centers around quickly reacting to the active enemy target.

The Fleet: The enemy fleet consists of multiple ship types (Sloop, Brigantine, Frigate, Man-of-War, and a Dreadnought Boss) each with varying maximum health. Ships are spawned at fixed, non-overlapping positions on the map.

The Target: Only the first ship in the fleet that is not yet destroyed is considered the current target.

The Action (MOLE_DURATION): A physical button on the connected hardware flashes, corresponding to the current target. This "mole" state lasts for only 0.75 seconds.

Player Hit (PLAYER_HIT): Successfully pressing the correct button before time runs out deals immediate damage to the targeted ship and slightly heals the player's Fortress health by 0.5.

Player Miss/Escape (PLAYER_MISS or MOLE_ESCAPED): Failing to hit the target causes the enemy ship to fire back, reducing the Player Fortress health by 1.

## Win and Loss Conditions
The game ends and a score is tallied when one of the following conditions is met:

VICTORY: All enemy ships in the fleet are sunk (get_current_target_ship() is None).

DEFEAT: The Player Ship/Fortress health reaches zero or less.

TIME'S UP: The GAME_DURATION expires.

## Hardware and Automation Integration
The game is intended to be run on a dedicated device ( Raspberry Pi) and includes integration points for external systems:

Input Hardware: The game uses evdev to monitor input events, expecting 9 physical buttons connected to the machine (via Picade X Hat).

Hardware used: Raspberry Pi 4, Primoni Picade X HAT and Primoni Plasma Button Kit.

Ansible Integration: Upon entering the "GAME_OVER" state, the game initiates a call to an external Ansible Automation Platform (AAP/AWX) API URL to launch a job template, passing the final score.
