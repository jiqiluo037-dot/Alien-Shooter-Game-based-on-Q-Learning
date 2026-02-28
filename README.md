# Alien Shooter - Q-Learning Agent

## Project Overview
This project implements an AI agent for an alien shooter game based on the Double Q-Learning reinforcement learning algorithm. Within the game, the AI controls the player's spacecraft to shoot aliens, collect power-ups (attack boost, full-screen clear, double score, shield), and survive for as long as possible across varying difficulty levels (target: 1 minute). The project encompasses a complete game environment, reinforcement learning agent, training workflow, and results visualisation module.

### Core Features
- 2D shooter environment built with Pygame
- Double Q-Learning reinforcement learning algorithm (addresses overestimation issues in standard Q-Learning)
- Three difficulty modes (Easy/Normal/Hard) with dynamic adjustment
- Multi-item system (attack penetration, full-screen clear, triple score, shield protection)
- Training process visualisation (reward curve, score curve, success rate comparison)
- Game UI optimisations including safe zone alerts and shield effects

## Environment Configuration

### Base Environment
- Python 3.8+ (3.9/3.10 recommended)
- Pygame 2.1.0+
- NumPy 1.21.0+
- Matplotlib 3.5.0+

### Installing Dependencies
```bash
pip install pygame==2.1.0 numpy==1.21.6 matplotlib==3.5.3
