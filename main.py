import pygame
import random
import math

# Nastavitve
WIDTH, HEIGHT = 800, 600
AGENT_COUNT = 50

# Inicializacija
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

class Obstacle:
    def __init__(self, x, y, radius):
        self.position = pygame.math.Vector2(x, y)
        self.radius = radius

    def draw(self, screen):
        pygame.draw.circle(screen, (200, 50, 50), (int(self.position.x), int(self.position.y)), self.radius)


# Agent
class Agent:
    def __init__(self, x, y):
        self.position = pygame.math.Vector2(x, y)
        self.velocity = pygame.math.Vector2(random.uniform(-2, 2), random.uniform(-2, 2))
        self.acceleration = pygame.math.Vector2(0, 0)
        self.max_speed = 1
        self.max_force = 0.03
        self.wander_angle = 0
        self.image_orig = pygame.image.load("Blobfish Spritesheet.png").convert_alpha()
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
        angle = self.velocity.angle_to(pygame.math.Vector2(1, 0)) * -1  # obrni za Pygame
        self.image = pygame.transform.rotate(self.image_orig, angle)
        self.rect = self.image.get_rect(center=self.position)
        screen.blit(self.image, self.rect.topleft)

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

    def stay_in_bounds(self, width, height, margin=50):
        desired = None

        if self.position.x < margin:
            desired = pygame.math.Vector2(self.max_speed, self.velocity.y)
        elif self.position.x > width - margin:
            desired = pygame.math.Vector2(-self.max_speed, self.velocity.y)

        if self.position.y < margin:
            if desired:
                desired.y = self.max_speed
            else:
                desired = pygame.math.Vector2(self.velocity.x, self.max_speed)
        elif self.position.y > height - margin:
            if desired:
                desired.y = -self.max_speed
            else:
                desired = pygame.math.Vector2(self.velocity.x, -self.max_speed)

        if desired:
            desired = desired.normalize() * self.max_speed
            steer = desired - self.velocity
            if steer.length() > self.max_force:
                steer.scale_to_length(self.max_force)
            self.apply_force(steer)

    def separate(self, agents, desired_separation=25):
        steer = pygame.math.Vector2(0, 0)
        total = 0

        for other in agents:
            if other == self:
                continue
            distance = self.position.distance_to(other.position)
            if 0 < distance < desired_separation:
                diff = self.position - other.position
                diff = diff.normalize() / distance  # bolj oddaljeni imajo manj vpliva
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

    def align(self, agents, neighbor_dist=50):
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

    def cohesion(self, agents, neighbor_dist=50):
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
                steer *= 1.5  # 💥 okrepljena sila izogibanja
                self.apply_force(steer)




agents = [Agent(random.randint(0, WIDTH), random.randint(0, HEIGHT)) for _ in range(AGENT_COUNT)]

obstacles = [
    Obstacle(300, 300, 30),
    Obstacle(500, 200, 40)
]

running = True
while running:
    screen.fill((0, 0, 0))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    for agent in agents:
        #Nariši ovire
        agent.avoid_obstacles(obstacles)

        #FLOCK: agent se premika v skladu z drugimi agenti
        agent.flock(agents)

        #WANDER: naključno naravno gibanje
        agent.wander()

        #STAY IN BOUNDS: ostani v oknu
        agent.stay_in_bounds(WIDTH, HEIGHT)

        #Posodobi pozicijo in nariši
        agent.update()
        agent.draw(screen)

    for obstacle in obstacles:
        obstacle.draw(screen)

    pygame.display.flip()
    clock.tick(30)

pygame.quit()

