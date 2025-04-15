import pygame
import random
import math

WIDTH, HEIGHT = 1000, 800
AGENT_COUNT = 15  # za vsako jato posebej

SIMULATION_RECT = pygame.Rect(0, 0, 1000, 600)

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

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
    def __init__(self, x, y, color=(0, 0, 0)):
        self.position = pygame.math.Vector2(x, y)
        self.velocity = pygame.math.Vector2(random.uniform(-2, 2), random.uniform(-2, 2))
        self.acceleration = pygame.math.Vector2(0, 0)
        self.max_speed = 2
        self.max_force = 0.25
        self.wander_angle = 0
        self.size = 15
        self.color = color

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
        angle = math.atan2(self.velocity.y, self.velocity.x)
        heading = pygame.math.Vector2(math.cos(angle), math.sin(angle))
        p1 = self.position + heading * self.size
        p2 = self.position + heading.rotate(135) * self.size * 0.5
        p3 = self.position + heading.rotate(-135) * self.size * 0.5
        pygame.draw.polygon(screen, self.color, [p1, p2, p3])

    def seek(self, target):
        desired = target - self.position
        distance = desired.length()
        if distance == 0:
            return
        slowing_radius = 100
        if distance < slowing_radius:
            speed = self.max_speed * (distance / slowing_radius)
        else:
            speed = self.max_speed
        desired = desired.normalize() * speed
        steer = desired - self.velocity
        if steer.length() > self.max_force:
            steer.scale_to_length(self.max_force)
        self.apply_force(steer)

    def wander(self):
        wander_radius = 50
        wander_distance = 80
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

    def stay_in_bounds(self, margin=20):
        left = SIMULATION_RECT.left + margin
        right = SIMULATION_RECT.right - margin
        top = SIMULATION_RECT.top + margin
        bottom = SIMULATION_RECT.bottom - margin
        steer = pygame.math.Vector2(0, 0)
        if self.position.x < left:
            steer += pygame.math.Vector2(self.max_speed, 0)
        elif self.position.x > right:
            steer += pygame.math.Vector2(-self.max_speed, 0)
        if self.position.y < top:
            steer += pygame.math.Vector2(0, self.max_speed)
        elif self.position.y > bottom:
            steer += pygame.math.Vector2(0, -self.max_speed)
        if steer.length() > 0:
            if steer.length() > self.max_force:
                steer.scale_to_length(self.max_force)
            steer *= 2
            self.apply_force(steer)

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

    def flock(self, agents):
        self.separate(agents)
        self.align(agents)
        self.cohesion(agents)

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

def create_flock1():
    return [Agent(random.randint(100, 400), random.randint(100, 500), color=(0, 0, 255)) for _ in range(AGENT_COUNT)]

def create_flock2():
    return [Agent(random.randint(600, 900), random.randint(100, 500), color=(255, 0, 0)) for _ in range(AGENT_COUNT)]

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

flock1 = create_flock1()
flock2 = create_flock2()
obstacles = create_obstacles()

buttons = [
    Button(20, 650, 200, 35, "Išči in pristani", USE_SEEK),
    Button(240, 650, 200, 35, "Nakljucna hoja", USE_WANDER),
    Button(460, 650, 200, 35, "Omejeni prostor", USE_BOUNDS),
    Button(680, 650, 200, 35, "Ovire", USE_AVOID),

    Button(20, 700, 200, 35, "Ločitev", USE_SEPARATION),
    Button(240, 700, 200, 35, "Poravnava", USE_ALIGNMENT),
    Button(460, 700, 200, 35, "Kohezija", USE_COHESION),

    Button(680, 700, 200, 35, "Jata", USE_FLOCK),

    Button(20, 750, 150, 35, "RESET", RESET_SIMULATION),
]

running = True
while running:
    screen.fill((200, 220, 255))
    pygame.draw.rect(screen,(255, 255, 255), SIMULATION_RECT)
    pygame.draw.rect(screen, (255, 255, 255), (0, 610, WIDTH, 270))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            for button in buttons:
                button.handle_click(event.pos)

    if RESET_SIMULATION[0]:
        flock1 = create_flock1()
        flock2 = create_flock2()
        for toggle in [USE_SEEK, USE_WANDER, USE_BOUNDS, USE_SEPARATION, USE_ALIGNMENT, USE_COHESION, USE_FLOCK, USE_AVOID]:
            toggle[0] = False
        RESET_SIMULATION[0] = False

    mouse_vector = pygame.math.Vector2(pygame.mouse.get_pos())

    for flock in [flock1, flock2]:
        for agent in flock:
            if USE_SEEK[0]: agent.seek(mouse_vector)
            if USE_FLOCK[0]: agent.flock(flock)
            else:
                if USE_SEPARATION[0]: agent.separate(flock)
                if USE_ALIGNMENT[0]: agent.align(flock)
                if USE_COHESION[0]: agent.cohesion(flock)
            if USE_WANDER[0]: agent.wander()
            if USE_AVOID[0]: agent.avoid_obstacles(obstacles)

            if USE_BOUNDS[0]: agent.stay_in_bounds()
            agent.update()
            agent.draw(screen)

    for obstacle in obstacles:
        if SIMULATION_RECT.collidepoint(obstacle.position):
            obstacle.draw(screen)

    for button in buttons:
        button.draw(screen, font)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
