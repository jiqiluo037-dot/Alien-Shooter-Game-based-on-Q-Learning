import pygame
import random
import math
import numpy as np
import matplotlib.pyplot as plt
import os
from pygame.locals import *

# ================== 游戏配置 ==================
SCREEN_WIDTH = 400
SCREEN_HEIGHT = 600
PLAYER_WIDTH = 40
PLAYER_HEIGHT = 40
PLAYER_SPEED = 8  # 玩家速度
BULLET_WIDTH = 4
BULLET_HEIGHT = 12
BULLET_SPEED = 10
ALIEN_SIZE = 20
ITEM_SIZE = 20
FPS = 60

# 颜色定义
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)
GRAY = (128, 128, 128)
LIGHT_GRAY = (200, 200, 200)
PURPLE = (128, 0, 128)
ORANGE = (255, 165, 0)

# 道具类型
ITEM_ATTACK = 1
ITEM_ELIMINATE = 2
ITEM_SCORE_X2 = 3
ITEM_SHIELD = 4  # 新增护盾道具

# 难度参数 - 修正后
DIFFICULTY = {
    'easy': {
        'alien_speed': 0.8,  # 适度提高速度
        'spawn_alien_prob': 0.003,  # 适度提高生成概率
        'spawn_item_prob': 0.012,  # 提高道具生成概率
        'max_aliens': 10,  # 适度增加外星人数量
        'time_limit': 60  # 1分钟游戏时间
    },
    'normal': {
        'alien_speed': 1.0,  # 适中速度
        'spawn_alien_prob': 0.0045,  # 适中生成概率
        'spawn_item_prob': 0.009,  # 适中道具生成概率
        'max_aliens': 12,  # 适中外星人数量
        'time_limit': 60  # 1分钟游戏时间
    },
    'difficult': {
        'alien_speed': 1.3,  # 较快速度
        'spawn_alien_prob': 0.006,  # 较高生成概率
        'spawn_item_prob': 0.007,  # 略低道具生成概率
        'max_aliens': 15,  # 较多外星人数量
        'time_limit': 60  # 1分钟游戏时间
    }
}

# Q-learning 参数
ALPHA = 0.1  # 降低学习率防止过拟合
GAMMA = 0.9  # 降低折扣因子
EPSILON_START = 0.98  # 更高的初始探索率
EPSILON_MIN = 0.05  # 最小探索率
EPSILON_DECAY = 0.9995  # 更慢的探索率衰减
NUM_EPISODES = 5000  # 5000轮
MAX_STEPS = 3600  # 60秒 * 60 FPS = 3600 步


# ================== 游戏环境 ==================
class AlienShooter:
    def __init__(self, render=False, difficulty='normal'):
        self.render = render
        self.difficulty = difficulty
        self.reset()
        if render:
            pygame.init()
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
            pygame.display.set_caption("Alien Shooter - Q-Learning")
            self.clock = pygame.time.Clock()
            self.load_assets()
        else:
            pygame.init()
            self.screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            self.clock = pygame.time.Clock()
            self.load_assets()  # 即使不渲染也要加载资源

    def load_assets(self):
        """加载游戏资源（图形和音效）"""
        # 背景
        try:
            self.background = pygame.image.load('background.png').convert()
            self.background = pygame.transform.scale(self.background, (SCREEN_WIDTH, SCREEN_HEIGHT))
        except:
            # 如果没有背景图片，使用渐变色背景
            self.background = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            for y in range(SCREEN_HEIGHT):
                color_value = int(40 * (1 - y / SCREEN_HEIGHT))
                self.background.fill((color_value, color_value, 40 + color_value),
                                     (0, y, SCREEN_WIDTH, 1))

        # 玩家
        self.player_img = pygame.Surface((PLAYER_WIDTH, PLAYER_HEIGHT), pygame.SRCALPHA)
        pygame.draw.polygon(self.player_img, CYAN,
                            [(PLAYER_WIDTH // 2, 0), (0, PLAYER_HEIGHT), (PLAYER_WIDTH, PLAYER_HEIGHT)])
        pygame.draw.rect(self.player_img, (0, 200, 200), (PLAYER_WIDTH // 2 - 3, PLAYER_HEIGHT // 2, 6, 6))  # 闪光

        # 外星人
        self.alien_img = pygame.Surface((ALIEN_SIZE, ALIEN_SIZE), pygame.SRCALPHA)
        pygame.draw.circle(self.alien_img, RED, (ALIEN_SIZE // 2, ALIEN_SIZE // 2), ALIEN_SIZE // 2)
        pygame.draw.circle(self.alien_img, WHITE, (ALIEN_SIZE // 2 - 3, ALIEN_SIZE // 2 - 3), 2)
        pygame.draw.circle(self.alien_img, WHITE, (ALIEN_SIZE // 2 + 3, ALIEN_SIZE // 2 - 3), 2)

        # 子弹
        self.bullet_img = pygame.Surface((BULLET_WIDTH, BULLET_HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(self.bullet_img, YELLOW, (0, 0, BULLET_WIDTH, BULLET_HEIGHT))
        pygame.draw.rect(self.bullet_img, (255, 255, 150), (1, 1, BULLET_WIDTH - 2, BULLET_HEIGHT - 2))

        # 道具
        self.item_imgs = {
            ITEM_ATTACK: pygame.Surface((ITEM_SIZE, ITEM_SIZE), pygame.SRCALPHA),
            ITEM_ELIMINATE: pygame.Surface((ITEM_SIZE, ITEM_SIZE), pygame.SRCALPHA),
            ITEM_SCORE_X2: pygame.Surface((ITEM_SIZE, ITEM_SIZE), pygame.SRCALPHA),
            ITEM_SHIELD: pygame.Surface((ITEM_SIZE, ITEM_SIZE), pygame.SRCALPHA)
        }

        # 攻击道具
        pygame.draw.polygon(self.item_imgs[ITEM_ATTACK], RED,
                            [(ITEM_SIZE // 2, 0), (0, ITEM_SIZE), (ITEM_SIZE, ITEM_SIZE)])
        pygame.draw.circle(self.item_imgs[ITEM_ATTACK], (255, 200, 0), (ITEM_SIZE // 2, ITEM_SIZE // 2), ITEM_SIZE // 4)

        # 消除道具
        pygame.draw.circle(self.item_imgs[ITEM_ELIMINATE], GREEN, (ITEM_SIZE // 2, ITEM_SIZE // 2), ITEM_SIZE // 2)
        pygame.draw.circle(self.item_imgs[ITEM_ELIMINATE], BLACK, (ITEM_SIZE // 2, ITEM_SIZE // 2), ITEM_SIZE // 4)

        # 2倍得分道具
        pygame.draw.rect(self.item_imgs[ITEM_SCORE_X2], BLUE, (0, 0, ITEM_SIZE, ITEM_SIZE))
        pygame.draw.rect(self.item_imgs[ITEM_SCORE_X2], (0, 0, 200), (2, 2, ITEM_SIZE - 4, ITEM_SIZE - 4))
        pygame.draw.rect(self.item_imgs[ITEM_SCORE_X2], YELLOW, (5, 5, ITEM_SIZE - 10, ITEM_SIZE - 10))

        # 护盾道具
        pygame.draw.circle(self.item_imgs[ITEM_SHIELD], PURPLE, (ITEM_SIZE // 2, ITEM_SIZE // 2), ITEM_SIZE // 2)
        pygame.draw.circle(self.item_imgs[ITEM_SHIELD], WHITE, (ITEM_SIZE // 2, ITEM_SIZE // 2), ITEM_SIZE // 4)

        # 音效
        try:
            self.shoot_sound = pygame.mixer.Sound('shoot.wav')
            self.hit_sound = pygame.mixer.Sound('hit.wav')
            self.item_sound = pygame.mixer.Sound('item.wav')
            self.shield_sound = pygame.mixer.Sound('shield.wav')
        except:
            # 如果没有音效文件，使用空函数
            self.shoot_sound = lambda: None
            self.hit_sound = lambda: None
            self.item_sound = lambda: None
            self.shield_sound = lambda: None

    def reset(self):
        self.player_rect = pygame.Rect(SCREEN_WIDTH // 2 - PLAYER_WIDTH // 2, SCREEN_HEIGHT - PLAYER_HEIGHT - 10,
                                       PLAYER_WIDTH, PLAYER_HEIGHT)
        self.aliens = []
        self.bullets = []
        self.items = []
        self.score = 0
        self.lives = 3
        self.attack_penetrate = False
        self.score_multiplier = 1
        self.buff_timer_attack = 0
        self.buff_timer_score = 0
        self.buff_timer_shield = 0  # 新增护盾buff计时器
        self.frame_count = 0
        self.done = False
        self.start_time = pygame.time.get_ticks()

        # 重置道具状态
        self.active_shield = False
        self.shield_cooldown = 0

        # 安全区闪烁相关
        self.safety_flash = False
        self.flash_timer = 0
        self.flash_state = False

        # 难度参数
        params = DIFFICULTY[self.difficulty]
        self.alien_speed = params['alien_speed']
        self.spawn_alien_prob = params['spawn_alien_prob']
        self.max_aliens = params['max_aliens']
        self.time_limit = params['time_limit']

        # 生成初始外星人
        for _ in range(1):
            self._spawn_alien()

        return self._get_state()

    def _spawn_alien(self):
        if len(self.aliens) < self.max_aliens:
            x = random.randint(ALIEN_SIZE, SCREEN_WIDTH - ALIEN_SIZE)
            y = random.randint(-ALIEN_SIZE, 30)
            alien_rect = pygame.Rect(x, y, ALIEN_SIZE, ALIEN_SIZE)
            self.aliens.append(alien_rect)

    def _spawn_item(self):
        if len(self.items) < 5:  # 减少同时存在的道具数量
            x = random.randint(ITEM_SIZE, SCREEN_WIDTH - ITEM_SIZE)
            y = random.randint(-ITEM_SIZE, 50)
            item_type = random.choice([ITEM_ATTACK, ITEM_ELIMINATE, ITEM_SCORE_X2, ITEM_SHIELD])  # 新增护盾道具
            item_rect = pygame.Rect(x, y, ITEM_SIZE, ITEM_SIZE)
            self.items.append((item_rect, item_type))

    def _shoot_bullet(self):
        bullet_rect = pygame.Rect(self.player_rect.centerx - BULLET_WIDTH // 2, self.player_rect.top, BULLET_WIDTH,
                                  BULLET_HEIGHT)
        self.bullets.append(bullet_rect)
        self.shoot_sound()

    def _apply_item_effect(self, item_type):
        if item_type == ITEM_ATTACK:
            self.attack_penetrate = True
            self.buff_timer_attack = 300
            self.item_sound()
        elif item_type == ITEM_ELIMINATE:
            num_remove = max(1, len(self.aliens) // 3)
            if self.aliens:
                to_remove = random.sample(self.aliens, min(num_remove, len(self.aliens)))
                for alien in to_remove:
                    self.aliens.remove(alien)
            self.item_sound()
        elif item_type == ITEM_SCORE_X2:
            self.score_multiplier = 3
            self.buff_timer_score = 300
            self.item_sound()
        elif item_type == ITEM_SHIELD:  # 新增护盾效果
            self.active_shield = True
            self.buff_timer_shield = 600  # 10秒护盾
            self.shield_sound()
            self.shield_cooldown = 300  # 护盾冷却时间

    def _update_buffs(self):
        if self.buff_timer_attack > 0:
            self.buff_timer_attack -= 1
            if self.buff_timer_attack <= 0:
                self.attack_penetrate = False

        if self.buff_timer_score > 0:
            self.buff_timer_score -= 1
            if self.buff_timer_score <= 0:
                self.score_multiplier = 1

        if self.buff_timer_shield > 0:  # 更新护盾buff
            self.buff_timer_shield -= 1
            if self.buff_timer_shield <= 0:
                self.active_shield = False

    def _update_difficulty(self):
        elapsed_seconds = (pygame.time.get_ticks() - self.start_time) / 1000.0
        # 降低难度随时间增长的速度
        inc = int(elapsed_seconds // 30)  # 每30秒才增加一次难度
        self.alien_speed = min(2.5, DIFFICULTY[self.difficulty]['alien_speed'] + inc * 0.05)
        self.spawn_alien_prob = min(0.025, DIFFICULTY[self.difficulty]['spawn_alien_prob'] + inc * 0.0005)

    def _check_safety_flash(self):
        """检测外星人是否接近安全区，触发闪烁提醒"""
        safety_line = self.player_rect.top
        # 检测是否有外星人在安全区上方50像素范围内
        for alien in self.aliens:
            if alien.bottom > safety_line - 50:
                self.safety_flash = True
                self.flash_timer = 60  # 闪烁1秒
                return
        self.safety_flash = False

    def _get_state(self):
        bin_width = SCREEN_WIDTH / 10
        player_bin = int(self.player_rect.centerx // bin_width)
        player_bin = min(9, max(0, player_bin))

        # 最近外星人
        nearest_alien_dir = 0
        nearest_alien_dist = 0
        min_alien_dist = float('inf')
        for alien in self.aliens:
            dx = alien.centerx - self.player_rect.centerx
            dy = alien.centery - self.player_rect.centery
            dist = math.hypot(dx, dy)
            if dist < min_alien_dist:
                min_alien_dist = dist
                if dx < -10:
                    nearest_alien_dir = 1
                elif dx > 10:
                    nearest_alien_dir = 2
                else:
                    nearest_alien_dir = 0

        # 外星人高度分段
        if min_alien_dist < 100:
            nearest_alien_dist = 1
        elif min_alien_dist < 200:
            nearest_alien_dist = 2
        else:
            nearest_alien_dist = 3

        # 最近道具
        nearest_item_dir = 0
        nearest_item_dist = 0
        nearest_item_type = 0
        min_item_dist = float('inf')
        for item_rect, item_type in self.items:
            dx = item_rect.centerx - self.player_rect.centerx
            dy = item_rect.centery - self.player_rect.centery
            dist = math.hypot(dx, dy)
            if dist < min_item_dist:
                min_item_dist = dist
                if dx < -10:
                    nearest_item_dir = 1
                elif dx > 10:
                    nearest_item_dir = 2
                else:
                    nearest_item_dir = 0

        # 道具高度分段
        if min_item_dist < 100:
            nearest_item_dist = 1
        elif min_item_dist < 200:
            nearest_item_dist = 2
        else:
            nearest_item_dist = 3

        nearest_item_type = 0
        if self.items:
            nearest_item_type = self.items[0][1]  # 取最近的道具类型

        # 添加护盾状态
        shield_state = 1 if self.active_shield else 0

        # 添加时间状态（归一化到0-1）
        elapsed_time = (pygame.time.get_ticks() - self.start_time) / 1000.0
        time_state = min(1.0, elapsed_time / self.time_limit)

        return (player_bin, nearest_alien_dir, nearest_alien_dist,
                nearest_item_dir, nearest_item_dist, nearest_item_type, shield_state, time_state)

    def step(self, action):
        if self.done:
            return self._get_state(), 0, True

        reward = 0
        # 1. 玩家移动
        if action == 0:  # 左
            self.player_rect.x -= PLAYER_SPEED
        elif action == 1:  # 右
            self.player_rect.x += PLAYER_SPEED
        elif action == 2:  # 射击（通过自动射击实现）
            pass  # 实际上每6帧自动射击
        elif action == 3:  # 护盾（被动效果）
            pass  # 护盾是被动的，通过道具获得

        # 限制玩家在屏幕内
        self.player_rect.x = max(0, min(SCREEN_WIDTH - PLAYER_WIDTH, self.player_rect.x))

        # 2. 更新难度
        self._update_difficulty()

        # 3. 生成新外星人和道具
        if random.random() < self.spawn_alien_prob:
            self._spawn_alien()
        if random.random() < 0.006:  # 固定道具生成率
            self._spawn_item()

        # 4. 自动发射子弹（每6帧一发）
        if self.frame_count % 6 == 0:
            self._shoot_bullet()

        # 5. 移动并更新所有对象
        # 先移动所有对象
        for bullet in self.bullets:
            bullet.y -= BULLET_SPEED

        for alien in self.aliens:
            alien.y += self.alien_speed

        for item_tuple in self.items:
            item_rect, _ = item_tuple
            item_rect.y += self.alien_speed * 0.7

        # 然后一次性清理出界对象
        self.bullets = [bullet for bullet in self.bullets if bullet.bottom >= 0]
        self.aliens = [alien for alien in self.aliens if alien.top <= SCREEN_HEIGHT]
        self.items = [item_tuple for item_tuple in self.items if item_tuple[0].top <= SCREEN_HEIGHT]

        # 8. 子弹与外星人碰撞（得分300）
        bullets_to_remove = set()
        aliens_to_remove = set()

        for i, bullet in enumerate(self.bullets):
            bullet_hit = False
            for j, alien in enumerate(self.aliens):
                if bullet.colliderect(alien):
                    reward += 300 * self.score_multiplier  # 增加得分
                    self.score += 300 * self.score_multiplier
                    aliens_to_remove.add(j)
                    self.hit_sound()
                    if not self.attack_penetrate:
                        bullets_to_remove.add(i)
                        bullet_hit = True
                    break
            if bullet_hit and not self.attack_penetrate:
                continue

        # 按索引倒序移除（避免索引变化问题）
        for idx in sorted(bullets_to_remove, reverse=True):
            if idx < len(self.bullets):
                del self.bullets[idx]
        for idx in sorted(aliens_to_remove, reverse=True):
            if idx < len(self.aliens):
                del self.aliens[idx]

        # 9. 玩家与道具碰撞
        items_to_remove = []
        for i, item_tuple in enumerate(self.items):
            item_rect, item_type = item_tuple
            if self.player_rect.colliderect(item_rect):
                items_to_remove.append(i)
                self._apply_item_effect(item_type)
                reward += 150  # 增加道具奖励
                self.score += 150
                break  # 每次只取一个道具

        # 按索引倒序移除道具
        for idx in sorted(items_to_remove, reverse=True):
            if idx < len(self.items):
                del self.items[idx]

        # 10. 外星人触碰玩家顶端安全区检测
        self._check_safety_flash()  # 检测是否需要闪烁提醒
        safety_line = self.player_rect.top
        aliens_to_remove = []
        alien_reach_safety = False  # 标记是否有外星人触碰安全区

        for i, alien in enumerate(self.aliens):
            if alien.bottom >= safety_line:
                aliens_to_remove.append(i)
                alien_reach_safety = True
                reward -= 100  # 触底惩罚加重
                self.score -= 50

        # 按索引倒序移除外星人
        for idx in sorted(aliens_to_remove, reverse=True):
            if idx < len(self.aliens):
                del self.aliens[idx]

        # 有外星人触碰安全区则扣除1点生命（护盾保护）
        if alien_reach_safety and not self.active_shield:
            self.lives -= 1
            reward -= 200  # 扣生命额外惩罚
            if self.lives <= 0:
                self.done = True

        # 11. 玩家与外星人碰撞（护盾保护）
        if not self.active_shield:
            aliens_to_remove = []
            for i, alien in enumerate(self.aliens):
                if self.player_rect.colliderect(alien):
                    aliens_to_remove.append(i)
                    self.lives -= 1
                    reward -= 100  # 降低惩罚
                    if self.lives <= 0:
                        self.done = True
                    break

            # 按索引倒序移除外星人
            for idx in sorted(aliens_to_remove, reverse=True):
                if idx < len(self.aliens):
                    del self.aliens[idx]

        # 12. 更新buff
        self._update_buffs()

        # 13. 更新闪烁状态
        if self.safety_flash and self.flash_timer > 0:
            self.flash_timer -= 1
            if self.frame_count % 5 == 0:  # 每5帧切换一次闪烁状态
                self.flash_state = not self.flash_state
        else:
            self.flash_state = False

        # 14. 更新护盾冷却
        if self.shield_cooldown > 0:
            self.shield_cooldown -= 1
            if self.shield_cooldown == 0:
                self.active_shield = False

        self.frame_count += 1
        if self.frame_count > MAX_STEPS:
            self.done = True

        # 15. 检查时间限制
        elapsed_time = (pygame.time.get_ticks() - self.start_time) / 1000.0
        if elapsed_time >= self.time_limit:
            self.done = True

        # 16. 每帧存活奖励
        reward += 0.5  # 每帧存活奖励
        # 生命值奖励 - 每剩余一条生命给予额外奖励
        reward += self.lives * 0.1

        next_state = self._get_state()
        return next_state, reward, self.done

    def render_game(self):
        if not self.render:
            return

        # 绘制背景
        self.screen.blit(self.background, (0, 0))

        # 绘制玩家
        self.screen.blit(self.player_img, (self.player_rect.x, self.player_rect.y))

        # 绘制子弹
        for bullet in self.bullets:
            self.screen.blit(self.bullet_img, (bullet.x, bullet.y))

        # 绘制外星人
        for alien in self.aliens:
            self.screen.blit(self.alien_img, (alien.x, alien.y))

        # 绘制道具
        for item_rect, item_type in self.items:
            self.screen.blit(self.item_imgs[item_type], (item_rect.x, item_rect.y))

        # 绘制护盾效果（如果激活）
        if self.active_shield:
            shield_radius = 30
            shield_surface = pygame.Surface((shield_radius * 2, shield_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(shield_surface, (200, 100, 255, 150), (shield_radius, shield_radius), shield_radius)
            self.screen.blit(shield_surface,
                             (self.player_rect.centerx - shield_radius, self.player_rect.centery - shield_radius))

        # 绘制安全线（玩家顶端）- 闪烁提醒
        safety_line_y = self.player_rect.top
        if self.flash_state:
            pygame.draw.line(self.screen, RED, (0, safety_line_y), (SCREEN_WIDTH, safety_line_y), 4)
        else:
            pygame.draw.line(self.screen, WHITE, (0, safety_line_y), (SCREEN_WIDTH, safety_line_y), 2)

        # 显示分数、时间、生命
        font = pygame.font.Font(None, 24)
        score_text = font.render(f"Score: {self.score}", True, WHITE)
        self.screen.blit(score_text, (10, 10))

        elapsed_seconds = (pygame.time.get_ticks() - self.start_time) / 1000.0
        time_text = font.render(f"Time: {elapsed_seconds:.1f}s/{self.time_limit}", True, WHITE)
        self.screen.blit(time_text, (10, 35))

        lives_text = font.render(f"Lives: {self.lives}", True, WHITE)
        self.screen.blit(lives_text, (10, 60))

        # 显示buff状态
        buff_text = ""
        if self.attack_penetrate:
            buff_text += "PEN "
        if self.score_multiplier > 1:
            buff_text += "x3 "
        if self.active_shield:
            buff_text += "SHIELD"
        if buff_text:
            buff_surf = font.render(buff_text, True, GREEN)
            self.screen.blit(buff_surf, (10, 85))

        # 显示AI决策
        if hasattr(self, 'last_action'):
            action_names = ["Left", "Right", "Shoot", "Shield"]
            action_text = font.render(f"AI Action: {action_names[self.last_action]}", True, YELLOW)
            self.screen.blit(action_text, (10, 110))

        pygame.display.flip()
        self.clock.tick(FPS)


# ================== Double Q-learning 智能体 ==================
class DoubleQLearningAgent:
    def __init__(self, actions, alpha=ALPHA, gamma=GAMMA, epsilon=EPSILON_START):
        self.actions = actions
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.q_table1 = {}  # 第一个Q表
        self.q_table2 = {}  # 第二个Q表
        self.action_counts = {}  # 记录每个动作的选择次数

    def _get_q(self, state, action, table_num=1):
        if table_num == 1:
            return self.q_table1.get((state, action), 0.0)
        else:
            return self.q_table2.get((state, action), 0.0)

    def choose_action(self, state):
        if random.random() < self.epsilon:
            return random.choice(self.actions)
        else:
            # 使用两个Q表的平均值来选择动作
            q_values1 = [self._get_q(state, a, 1) for a in self.actions]
            q_values2 = [self._get_q(state, a, 2) for a in self.actions]
            combined_q_values = [q1 + q2 for q1, q2 in zip(q_values1, q_values2)]
            max_q = max(combined_q_values)
            best_actions = [a for a, q in zip(self.actions, combined_q_values) if q == max_q]
            return random.choice(best_actions)

    def learn(self, state, action, reward, next_state, done):
        # 随机选择更新哪个Q表
        if random.random() < 0.5:
            # 更新Q表1
            current_q1 = self._get_q(state, action, 1)
            if done:
                target = reward
            else:
                # 使用Q表2来选择最优动作，用Q表1来评估
                q_values2 = [self._get_q(next_state, a, 2) for a in self.actions]
                best_action_idx = q_values2.index(max(q_values2))
                best_action = self.actions[best_action_idx]
                target = reward + self.gamma * self._get_q(next_state, best_action, 1)
            new_q = current_q1 + self.alpha * (target - current_q1)
            self.q_table1[(state, action)] = new_q
        else:
            # 更新Q表2
            current_q2 = self._get_q(state, action, 2)
            if done:
                target = reward
            else:
                # 使用Q表1来选择最优动作，用Q表2来评估
                q_values1 = [self._get_q(next_state, a, 1) for a in self.actions]
                best_action_idx = q_values1.index(max(q_values1))
                best_action = self.actions[best_action_idx]
                target = reward + self.gamma * self._get_q(next_state, best_action, 2)
            new_q = current_q2 + self.alpha * (target - current_q2)
            self.q_table2[(state, action)] = new_q

        # 更新动作计数
        if (state, action) not in self.action_counts:
            self.action_counts[(state, action)] = 0
        self.action_counts[(state, action)] += 1

    def decay_epsilon(self):
        self.epsilon = max(EPSILON_MIN, self.epsilon * EPSILON_DECAY)


# ================== 训练 ==================
def train():
    print("开始训练智能体，请耐心等待...")

    # 为每个难度单独训练
    results = {}

    for difficulty in ['easy', 'normal', 'difficult']:
        print(f"\n正在训练 {difficulty} 难度的AI...（5000轮）")
        env = AlienShooter(render=False, difficulty=difficulty)
        agent = DoubleQLearningAgent(actions=[0, 1, 2, 3])  # 0:左, 1:右, 2:射击, 3:护盾

        # 存储训练数据
        episode_rewards = []
        episode_scores = []
        episode_lives_used = []
        episode_durations = []
        success_count = 0
        failure_count = 0

        for ep in range(NUM_EPISODES):
            state = env.reset()
            total_reward = 0
            steps = 0
            done = False
            start_lives = env.lives

            while not done and steps < MAX_STEPS:
                action = agent.choose_action(state)
                next_state, reward, done = env.step(action)
                agent.learn(state, action, reward, next_state, done)
                state = next_state
                total_reward += reward
                steps += 1

                # 保存AI决策用于可视化
                env.last_action = action

            agent.decay_epsilon()
            episode_rewards.append(total_reward)
            episode_scores.append(env.score)
            episode_lives_used.append(start_lives - env.lives)
            duration = (pygame.time.get_ticks() - env.start_time) / 1000.0
            episode_durations.append(duration)

            # 统计成功和失败
            if env.lives > 0:
                success_count += 1
            else:
                failure_count += 1

            if (ep + 1) % 500 == 0:
                avg_reward = np.mean(episode_rewards[-500:])
                avg_score = np.mean(episode_scores[-500:])
                avg_lives = np.mean(episode_lives_used[-500:])
                avg_duration = np.mean(episode_durations[-500:])
                success_rate = success_count / (ep + 1) * 100
                print(f"{difficulty} - Episode {ep + 1}: avg reward {avg_reward:.1f}, avg score {avg_score:.1f}, "
                      f"avg lives lost {avg_lives:.2f}, avg duration {avg_duration:.1f}s, "
                      f"success rate {success_rate:.1f}%, epsilon {agent.epsilon:.3f}")

        # 保存结果
        results[difficulty] = {
            'rewards': episode_rewards,
            'scores': episode_scores,
            'durations': episode_durations,
            'lives_used': episode_lives_used,
            'success_count': success_count,
            'failure_count': failure_count,
            'agent': agent,
            'final_success_rate': success_count / NUM_EPISODES * 100
        }

        print(f"{difficulty} 难度最终成功率: {results[difficulty]['final_success_rate']:.1f}%")

    # 为每个难度分别绘制图表
    for difficulty in ['easy', 'normal', 'difficult']:
        data = results[difficulty]

        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        fig.suptitle(f'Training Results - {difficulty.capitalize()} Difficulty', fontsize=16)

        # 奖励曲线
        axes[0, 0].plot(data['rewards'], alpha=0.3, label='Raw Reward')
        smooth_rewards = [np.mean(data['rewards'][max(0, i - 200):i + 1]) for i in range(len(data['rewards']))]
        axes[0, 0].plot(smooth_rewards, label='Smoothed Reward', linewidth=2)
        axes[0, 0].set_title('Total Reward per Episode')
        axes[0, 0].set_xlabel('Episode')
        axes[0, 0].set_ylabel('Reward')
        axes[0, 0].legend()
        axes[0, 0].grid(True, linestyle='--', alpha=0.6)

        # 得分曲线
        axes[0, 1].plot(data['scores'], alpha=0.3, label='Raw Score')
        smooth_scores = [np.mean(data['scores'][max(0, i - 200):i + 1]) for i in range(len(data['scores']))]
        axes[0, 1].plot(smooth_scores, label='Smoothed Score', linewidth=2, color='orange')
        axes[0, 1].set_title('Score per Episode')
        axes[0, 1].set_xlabel('Episode')
        axes[0, 1].set_ylabel('Score')
        axes[0, 1].legend()
        axes[0, 1].grid(True, linestyle='--', alpha=0.6)

        # 生存时间曲线
        axes[1, 0].plot(data['durations'], alpha=0.3, label='Raw Duration')
        smooth_durations = [np.mean(data['durations'][max(0, i - 200):i + 1]) for i in range(len(data['durations']))]
        axes[1, 0].plot(smooth_durations, label='Smoothed Duration', linewidth=2, color='green')
        axes[1, 0].set_title('Game Duration per Episode')
        axes[1, 0].set_xlabel('Episode')
        axes[1, 0].set_ylabel('Duration (seconds)')
        axes[1, 0].legend()
        axes[1, 0].grid(True, linestyle='--', alpha=0.6)

        # 成功率曲线（每100轮计算一次）
        success_rates = []
        window_size = 100
        for i in range(window_size, len(data['rewards']), window_size):
            successes_in_window = sum(1 for j in range(i - window_size, i)
                                      if data['lives_used'][j] < 3)
            success_rates.append(successes_in_window / window_size * 100)

        if success_rates:
            episodes = list(range(window_size, len(data['rewards']), window_size))
            axes[1, 1].plot(episodes, success_rates, label='Success Rate', linewidth=2, color='purple')
            axes[1, 1].axhline(y=data['final_success_rate'], color='red', linestyle='--',
                               label=f'Final Rate: {data["final_success_rate"]:.1f}%')
            axes[1, 1].set_title('Success Rate per Window')
            axes[1, 1].set_xlabel('Episode')
            axes[1, 1].set_ylabel('Success Rate (%)')
            axes[1, 1].legend()
            axes[1, 1].grid(True, linestyle='--', alpha=0.6)
        else:
            axes[1, 1].text(0.5, 0.5, 'Not enough data\nfor success rate plot',
                            horizontalalignment='center', verticalalignment='center',
                            transform=axes[1, 1].transAxes, fontsize=12)
            axes[1, 1].set_title('Success Rate')

        plt.tight_layout()
        plt.savefig(f'training_results_{difficulty}.png')
        plt.show()

    # 综合比较图
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))

    # 比较最终成功率
    difficulties = list(results.keys())
    final_success_rates = [results[d]['final_success_rate'] for d in difficulties]

    bars = axes[0].bar(difficulties, final_success_rates,
                       color=['lightgreen', 'gold', 'lightcoral'])
    axes[0].set_title('Final Success Rates by Difficulty')
    axes[0].set_xlabel('Difficulty')
    axes[0].set_ylabel('Success Rate (%)')

    # 添加数值标签
    for bar, rate in zip(bars, final_success_rates):
        height = bar.get_height()
        axes[0].text(bar.get_x() + bar.get_width() / 2., height + 0.5,
                     f'{rate:.1f}%', ha='center', va='bottom')

    # 比较平均得分
    avg_scores = [np.mean(results[d]['scores']) for d in difficulties]

    bars2 = axes[1].bar(difficulties, avg_scores,
                        color=['lightblue', 'wheat', 'mistyrose'])
    axes[1].set_title('Average Scores by Difficulty')
    axes[1].set_xlabel('Difficulty')
    axes[1].set_ylabel('Average Score')

    # 添加数值标签
    for bar, score in zip(bars2, avg_scores):
        height = bar.get_height()
        axes[1].text(bar.get_x() + bar.get_width() / 2., height + 10,
                     f'{int(score)}', ha='center', va='bottom')

    plt.tight_layout()
    plt.savefig('comparative_results.png')
    plt.show()

    print("\n训练完成！返回所有难度的AI代理...")
    return results


# ================== 开始界面 ==================
def show_start_screen(screen):
    screen.fill(BLACK)
    font_title = pygame.font.Font(None, 60)
    font_btn = pygame.font.Font(None, 40)
    font_small = pygame.font.Font(None, 24)

    title = font_title.render("Alien Shooter", True, WHITE)
    screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 50))

    # 游戏说明
    instructions = [
        "AI-controlled player will attempt to survive",
        "for 1 minute while shooting aliens",
        "and collecting power-ups"
    ]

    for i, line in enumerate(instructions):
        text = font_small.render(line, True, LIGHT_GRAY)
        screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, 120 + i * 30))

    btn_easy = pygame.Rect(SCREEN_WIDTH // 2 - 150, 220, 300, 60)
    btn_normal = pygame.Rect(SCREEN_WIDTH // 2 - 150, 300, 300, 60)
    btn_difficult = pygame.Rect(SCREEN_WIDTH // 2 - 150, 380, 300, 60)

    pygame.draw.rect(screen, (100, 200, 100), btn_easy, border_radius=15)
    pygame.draw.rect(screen, (200, 200, 100), btn_normal, border_radius=15)
    pygame.draw.rect(screen, (200, 100, 100), btn_difficult, border_radius=15)

    text_easy = font_btn.render("Easy", True, BLACK)
    text_normal = font_btn.render("Normal", True, BLACK)
    text_difficult = font_btn.render("Difficult", True, BLACK)

    screen.blit(text_easy,
                (btn_easy.centerx - text_easy.get_width() // 2, btn_easy.centery - text_easy.get_height() // 2))
    screen.blit(text_normal,
                (btn_normal.centerx - text_normal.get_width() // 2, btn_normal.centery - text_normal.get_height() // 2))
    screen.blit(text_difficult, (btn_difficult.centerx - text_difficult.get_width() // 2,
                                 btn_difficult.centery - text_difficult.get_height() // 2))

    # 显示难度说明
    easy_desc = font_small.render("Slower aliens, fewer spawns, more items", True, LIGHT_GRAY)
    normal_desc = font_small.render("Moderate speed and spawns", True, LIGHT_GRAY)
    difficult_desc = font_small.render("Faster aliens, more spawns", True, LIGHT_GRAY)

    screen.blit(easy_desc, (SCREEN_WIDTH // 2 - easy_desc.get_width() // 2, 285))
    screen.blit(normal_desc, (SCREEN_WIDTH // 2 - normal_desc.get_width() // 2, 365))
    screen.blit(difficult_desc, (SCREEN_WIDTH // 2 - difficult_desc.get_width() // 2, 445))

    pygame.display.flip()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.MOUSEBUTTONDOWN:
                x, y = event.pos
                if btn_easy.collidepoint(x, y):
                    return 'easy'
                elif btn_normal.collidepoint(x, y):
                    return 'normal'
                elif btn_difficult.collidepoint(x, y):
                    return 'difficult'
        pygame.time.wait(50)


# ================== 游戏结束总结界面 ==================
def show_game_over_screen(screen, score, duration, current_difficulty, lives_left):
    # 创建半透明遮罩
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    overlay.set_alpha(200)
    overlay.fill(BLACK)
    screen.blit(overlay, (0, 0))

    # 字体设置
    font_title = pygame.font.Font(None, 70)
    font_info = pygame.font.Font(None, 40)
    font_btn = pygame.font.Font(None, 36)
    font_small = pygame.font.Font(None, 24)

    # 标题
    game_over_text = font_title.render("Game Over", True, RED)
    screen.blit(game_over_text, (SCREEN_WIDTH // 2 - game_over_text.get_width() // 2, 80))

    # 分数和时间
    score_text = font_info.render(f"Final Score: {score}", True, YELLOW)
    screen.blit(score_text, (SCREEN_WIDTH // 2 - score_text.get_width() // 2, 180))

    time_text = font_info.render(f"Time: {duration:.1f}s", True, CYAN)
    screen.blit(time_text, (SCREEN_WIDTH // 2 - time_text.get_width() // 2, 240))

    # 生命值
    lives_text = font_info.render(f"Lives Left: {lives_left}", True, GREEN)
    screen.blit(lives_text, (SCREEN_WIDTH // 2 - lives_text.get_width() // 2, 300))

    # 难度信息
    diff_text = font_info.render(f"Difficulty: {current_difficulty.capitalize()}", True, WHITE)
    screen.blit(diff_text, (SCREEN_WIDTH // 2 - diff_text.get_width() // 2, 360))

    # 结果说明
    if lives_left > 0:
        result_text = font_info.render("Survived the full minute!", True, GREEN)
    else:
        result_text = font_info.render("All lives lost", True, RED)
    screen.blit(result_text, (SCREEN_WIDTH // 2 - result_text.get_width() // 2, 420))

    # 按钮
    btn_restart = pygame.Rect(SCREEN_WIDTH // 2 - 160, 480, 140, 60)
    btn_menu = pygame.Rect(SCREEN_WIDTH // 2 + 20, 480, 140, 60)

    # 绘制按钮
    pygame.draw.rect(screen, (0, 200, 0), btn_restart, border_radius=15)
    pygame.draw.rect(screen, (200, 0, 0), btn_menu, border_radius=15)

    # 按钮文字
    restart_text = font_btn.render("Restart", True, BLACK)
    menu_text = font_btn.render("Menu", True, BLACK)

    screen.blit(restart_text, (btn_restart.centerx - restart_text.get_width() // 2,
                               btn_restart.centery - restart_text.get_height() // 2))
    screen.blit(menu_text, (btn_menu.centerx - menu_text.get_width() // 2,
                            btn_menu.centery - menu_text.get_height() // 2))

    pygame.display.flip()

    # 等待用户操作
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return 'quit'
            if event.type == pygame.MOUSEBUTTONDOWN:
                x, y = event.pos
                if btn_restart.collidepoint(x, y):
                    return 'restart'
                elif btn_menu.collidepoint(x, y):
                    return 'menu'
        pygame.time.wait(50)


# ================== 演示 ==================
def run_game(trained_results, difficulty):
    while True:
        # 获取对应难度的AI代理
        agent = trained_results[difficulty]['agent']
        env = AlienShooter(render=True, difficulty=difficulty)
        state = env.reset()
        done = False
        total_reward = 0

        while not done:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return

            action = agent.choose_action(state)
            next_state, reward, done = env.step(action)
            state = next_state
            total_reward += reward
            env.render_game()

        # 计算游戏时长
        duration = (pygame.time.get_ticks() - env.start_time) / 1000.0
        lives_left = env.lives
        print(f"Game over. Final score: {env.score}, Time: {duration:.1f}s, Lives left: {lives_left}")

        # 显示游戏结束界面
        result = show_game_over_screen(env.screen, env.score, duration, difficulty, lives_left)

        if result == 'restart':
            continue  # 重新开始当前难度
        elif result == 'menu':
            # 返回开始界面
            pygame.display.set_caption("Alien Shooter - Start")
            new_difficulty = show_start_screen(env.screen)
            if new_difficulty is None:
                pygame.quit()
                return
            difficulty = new_difficulty
        elif result == 'quit':
            pygame.quit()
            return


# ================== 主程序 ==================
if __name__ == "__main__":
    # 确保音效文件存在（如果没有，会使用空函数）
    try:
        pygame.mixer.init()
    except:
        pass

    # 训练AI
    trained_results = train()

    # 显示开始界面
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Alien Shooter - Start")

    difficulty = show_start_screen(screen)
    if difficulty is None:
        pygame.quit()
        exit()

    # 运行游戏
    run_game(trained_results, difficulty)