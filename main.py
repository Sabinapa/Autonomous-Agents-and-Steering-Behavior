import pygame
import random
import math

WIDTH, HEIGHT = 1000, 1000
AGENT_COUNT = 30

SIMULATION_RECT = pygame.Rect(50, 50, 900, 600)

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

# Font for button labels
pygame.font.init()
font = pygame.font.SysFont("Consolas", 18)

class Button:
    def __init__(self, x, y, width, height, label, toggle_ref):
        self.rect = pygame.Rect(x, y, width, height)
        self.label = label
        self.toggle_ref = toggle_ref

    def draw(self, screen, font):
        color = (100, 200, 100) if self.toggle_ref[0] else (200, 100, 100)
        pygame.draw.rect(screen, color, self.rect, border_radius=8)
        text = font.render(self.label, True, (0, 0, 0))
        text_rect = text.get_rect(center=self.rect.center)
        screen.blit(text, text_rect)

    def handle_click(self, pos):
        if self.rect.collidepoint(pos):
            if self.label == "RESET":
                self.toggle_ref[0] = True
            else:
                self.toggle_ref[0] = not self.toggle_ref[0]

USE_SEEK = [False]
USE_WANDER = [False]
USE_BOUNDS = [True]
USE_SEPARATION = [False]
USE_ALIGNMENT = [False]
USE_COHESION = [False]
USE_FLOCK = [False]
USE_AVOID = [False]
RESET_SIMULATION = [False]

class Obstacle:
    def __init__(self, x, y, radius):
        self.position = pygame.math.Vector2(x, y)
        self.radius = radius

    def draw(self, screen):
        gradient_surface = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        center = self.radius

        for i in range(self.radius, 0, -1):
            r = 75 + int((128 - 75) * (i / self.radius))
            g = 0
            b = 130 + int((255 - 130) * (i / self.radius))
            alpha = int(255 * (i / self.radius) * 0.6)

            pygame.draw.circle(gradient_surface, (r, g, b, alpha), (center, center), i)

        screen.blit(gradient_surface, (int(self.position.x - self.radius), int(self.position.y - self.radius)))

class Agent:
    def __init__(self, x, y):
        self.position = pygame.math.Vector2(x, y)
        self.velocity = pygame.math.Vector2(random.uniform(-2, 2), random.uniform(-2, 2))
        self.acceleration = pygame.math.Vector2(0, 0)
        self.max_speed = 1
        self.max_force = 0.03
        self.wander_angle = 0
        self.image_orig = pygame.image.load("fish2Texture.png").convert_alpha()
        self.image_orig = pygame.transform.scale(self.image_orig, (52, 31))
        self.image = self.image_orig.copy()
        self.rect = self.image.get_rect(center=self.position)

    def update(self):
        self.velocity += self.acceleration
        if self.velocity.length() > self.max_speed:
            self.velocity.scale_to_length(self.max_speed)
        self.position += self.velocity
        self.acceleration *= 0

    def apply_force(self, force):
        self.acceleration += force

    def draw(self, screen):
        if not SIMULATION_RECT.collidepoint(self.position):
            return
        angle = self.velocity.angle_to(pygame.math.Vector2(1, 0)) * -1
        self.image = pygame.transform.rotate(self.image_orig, angle)
        self.rect = self.image.get_rect(center=self.position)
        screen.blit(self.image, self.rect.topleft)

    # 1. Isci in pristani
    def seek(self, target):
        desired = target - self.position
        distance = desired.length()
        if distance == 0:
            return

        slowing_radius = 100  # Dodamo deceleration radius
        if distance < slowing_radius:  # Prilagaj hitrost glede na razdaljo
            speed = self.max_speed * (distance / slowing_radius)
        else:
            speed = self.max_speed

        desired = desired.normalize() * speed
        steer = desired - self.velocity

        if steer.length() > self.max_force:
            steer.scale_to_length(self.max_force)

        self.apply_force(steer)

    # 2. Nakljucna »naravna« hoja
    def wander(self):
        wander_radius = 50 #znotraj tega agent niha
        wander_distance = 80 #kako daleč od agentovega trenutnega položaja
        change = 0.3
        self.wander_angle += random.uniform(-change, change)
        if self.velocity.length() == 0:
            return
        circle_center = self.velocity.normalize() * wander_distance
        displacement = pygame.math.Vector2(wander_radius * math.cos(self.wander_angle),
                                           wander_radius * math.sin(self.wander_angle))
        wander_force = circle_center + displacement
        if wander_force.length() > self.max_force:
            wander_force.scale_to_length(self.max_force)
        self.apply_force(wander_force)

    # 3. Omejeni prostor
    def stay_in_bounds(self, margin=50):
        left = SIMULATION_RECT.left + margin
        right = SIMULATION_RECT.right - margin
        top = SIMULATION_RECT.top + margin
        bottom = SIMULATION_RECT.bottom - margin
        desired = None

        if self.position.x < left:
            desired = pygame.math.Vector2(self.max_speed, self.velocity.y)
        elif self.position.x > right:
            desired = pygame.math.Vector2(-self.max_speed, self.velocity.y)
        if self.position.y < top:
            desired = desired or pygame.math.Vector2(self.velocity.x, self.max_speed)
        elif self.position.y > bottom:
            desired = desired or pygame.math.Vector2(self.velocity.x, -self.max_speed)

        if desired:
            desired = desired.normalize() * self.max_speed
            steer = desired - self.velocity
            if steer.length() > self.max_force:
                steer.scale_to_length(self.max_force)
            self.apply_force(steer)

    # 4. Locitev
    def separate(self, agents, desired_separation=35):
        steer = pygame.math.Vector2(0, 0)
        total = 0
        for other in agents:
            if other == self:
                continue
            distance = self.position.distance_to(other.position)
            if 0 < distance < desired_separation:
                diff = self.position - other.position
                diff = diff.normalize() / distance
                steer += diff
                total += 1
        if total > 0:
            steer /= total
            if steer.length() > 0:
                steer = steer.normalize() * self.max_speed
                steer -= self.velocity
                if steer.length() > self.max_force:
                    steer.scale_to_length(self.max_force)
                self.apply_force(steer)

    # 5. Poravnava
    def align(self, agents, neighbor_dist=70):
        sum_velocity = pygame.math.Vector2(0, 0)
        total = 0
        for other in agents:
            if other == self:
                continue
            distance = self.position.distance_to(other.position)
            if distance < neighbor_dist:
                sum_velocity += other.velocity
                total += 1
        if total > 0:
            average = sum_velocity / total
            average = average.normalize() * self.max_speed
            steer = average - self.velocity
            if steer.length() > self.max_force:
                steer.scale_to_length(self.max_force)
            self.apply_force(steer)

    # 6. Kohezija
    def cohesion(self, agents, neighbor_dist=80):
        center_mass = pygame.math.Vector2(0, 0)
        total = 0
        for other in agents:
            if other == self:
                continue
            distance = self.position.distance_to(other.position)
            if distance < neighbor_dist:
                center_mass += other.position
                total += 1
        if total > 0:
            center_mass /= total
            self.seek(center_mass)

    # 7. Jata
    def flock(self, agents):
        self.separate(agents)
        self.align(agents)
        self.cohesion(agents)

    # 8. Izogibaj se oviram
    def avoid_obstacles(self, obstacles, avoid_radius=60):
        steer = pygame.math.Vector2(0, 0)
        total = 0
        for obs in obstacles:
            distance = self.position.distance_to(obs.position)
            if distance < obs.radius + avoid_radius:
                diff = self.position - obs.position
                if diff.length() > 0:
                    diff = diff.normalize() / distance
                    steer += diff
                    total += 1
        if total > 0:
            steer /= total
            if steer.length() > 0:
                steer = steer.normalize() * self.max_speed
                steer -= self.velocity
                if steer.length() > self.max_force:
                    steer.scale_to_length(self.max_force)
                steer *= 1.5
                self.apply_force(steer)

def create_agents():
    return [Agent(random.randint(SIMULATION_RECT.left, SIMULATION_RECT.right),
                  random.randint(SIMULATION_RECT.top, SIMULATION_RECT.bottom)) for _ in range(AGENT_COUNT)]

def create_obstacles():
    return [
        Obstacle(150, 150, 30),
        Obstacle(300, 250, 40),
        Obstacle(450, 150, 25),
        Obstacle(600, 300, 35),
        Obstacle(750, 200, 30),
        Obstacle(200, 500, 45),
        Obstacle(500, 550, 40),
        Obstacle(700, 500, 35),
        Obstacle(350, 650, 50),
        Obstacle(850, 400, 30)
    ]

agents = create_agents()
obstacles = create_obstacles()

buttons = [
    Button(20, 730, 200, 35, "Išči in pristani", USE_SEEK),
    Button(240, 730, 200, 35, "Nakljucna hoja", USE_WANDER),
    Button(460, 730, 200, 35, "Omejeni prostor", USE_BOUNDS),
    Button(680, 730, 200, 35, "Ovire", USE_AVOID),

    Button(20, 780, 200, 35, "Ločitev", USE_SEPARATION),
    Button(240, 780, 200, 35, "Poravnava", USE_ALIGNMENT),
    Button(460, 780, 200, 35, "Kohezija", USE_COHESION),

    Button(680, 780, 200, 35, "Jata", USE_FLOCK),

    Button(20, 830, 150, 35, "RESET", RESET_SIMULATION),
]

running = True
while running:
    screen.fill((200, 220, 255))
    pygame.draw.rect(screen,(255, 255, 255), SIMULATION_RECT)  # okno za simulacijo
    pygame.draw.rect(screen, (255, 255, 255), (0, 700, WIDTH, 270))  # spodnji panel

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            for button in buttons:
                button.handle_click(event.pos)

    if RESET_SIMULATION[0]:
        agents = create_agents()
        for toggle in [USE_SEEK, USE_WANDER, USE_BOUNDS, USE_SEPARATION, USE_ALIGNMENT, USE_COHESION, USE_FLOCK, USE_AVOID]:
            toggle[0] = False
        RESET_SIMULATION[0] = False

    mouse_vector = pygame.math.Vector2(pygame.mouse.get_pos())

    for agent in agents:
        if USE_BOUNDS[0]: agent.stay_in_bounds() # Ostani v meji
        if USE_SEEK[0]: agent.seek(mouse_vector) # Išči in pristani
        if USE_FLOCK[0]: agent.flock(agents) # Jata
        else:
            if USE_SEPARATION[0]: agent.separate(agents)
            if USE_ALIGNMENT[0]: agent.align(agents)
            if USE_COHESION[0]: agent.cohesion(agents)
        if USE_WANDER[0]: agent.wander() # Nakljucna hoja
        if USE_AVOID[0]: agent.avoid_obstacles(obstacles) # Izogibaj se ovir
        agent.update()
        agent.draw(screen)

    for obstacle in obstacles:
        if SIMULATION_RECT.collidepoint(obstacle.position):
            obstacle.draw(screen)

    for button in buttons:
        button.draw(screen, font)

    pygame.display.flip()
    clock.tick(30)

pygame.quit()
