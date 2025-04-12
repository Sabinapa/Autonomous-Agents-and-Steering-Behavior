import pygame
import random
import math

# Nastavitve
WIDTH, HEIGHT = 800, 600
AGENT_COUNT = 10

# Inicializacija
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

# Agent
class Agent:
    def __init__(self, x, y):
        self.position = pygame.math.Vector2(x, y)
        self.velocity = pygame.math.Vector2(random.uniform(-2, 2), random.uniform(-2, 2))
        self.acceleration = pygame.math.Vector2(0, 0)
        self.max_speed = 2
        self.max_force = 0.05
        self.wander_angle = 0

    def update(self):
        self.velocity += self.acceleration
        if self.velocity.length() > self.max_speed:
            self.velocity.scale_to_length(self.max_speed)
        self.position += self.velocity
        self.acceleration *= 0

    def apply_force(self, force):
        self.acceleration += force

    def draw(self, screen):
        pygame.draw.circle(screen, (255, 255, 255), (int(self.position.x), int(self.position.y)), 5)

    def seek(self, target):
        desired = target - self.position
        distance = desired.length()
        if distance == 0:
            return

        desired = desired.normalize() * self.max_speed
        steer = desired - self.velocity

        if steer.length() > self.max_force:
            steer.scale_to_length(self.max_force)

        self.apply_force(steer)

    def wander(self):
        # Nastavitve
        wander_radius = 50
        wander_distance = 80
        change = 0.3  # večja vrednost = večje spremembe smeri

        self.wander_angle += random.uniform(-change, change)

        # Izračun kroga pred agentom
        circle_center = self.velocity.normalize() * wander_distance
        displacement = pygame.math.Vector2(wander_radius * math.cos(self.wander_angle),
                                           wander_radius * math.sin(self.wander_angle))

        wander_force = circle_center + displacement

        if wander_force.length() > self.max_force:
            wander_force.scale_to_length(self.max_force)

        self.apply_force(wander_force)


agents = [Agent(random.randint(0, WIDTH), random.randint(0, HEIGHT)) for _ in range(AGENT_COUNT)]

running = True
while running:
    screen.fill((0, 0, 0))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    mouse_pos = pygame.mouse.get_pos()
    mouse_vector = pygame.math.Vector2(mouse_pos)

    for agent in agents:
        agent.wander()
        agent.update()
        agent.draw(screen)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()

