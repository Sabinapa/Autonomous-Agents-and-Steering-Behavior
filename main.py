import pygame
import random
import math

WIDTH, HEIGHT = 1000, 800
AGENT_COUNT = 15

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

        for i in range(self.radius, 0, -1): #gradient
            r = 75 + int((128 - 75) * (i / self.radius))
            g = 0
            b = 130 + int((255 - 130) * (i / self.radius))
            alpha = int(255 * (i / self.radius) * 0.6)

            pygame.draw.circle(gradient_surface, (r, g, b, alpha), (center, center), i)

        screen.blit(gradient_surface, (int(self.position.x - self.radius), int(self.position.y - self.radius)))

class Agent:
    def __init__(self, x, y, color=(0, 0, 0)):
        self.position = pygame.math.Vector2(x, y) #trenutna pozicija
        self.velocity = pygame.math.Vector2(random.uniform(-2, 2), random.uniform(-2, 2)) #hitrost
        self.acceleration = pygame.math.Vector2(0, 0) #pospešek
        self.max_speed = 2 # najvecja hitrost
        self.max_force = 0.25 # najvecja sila, ki jo lahko agent uporabi
        self.wander_angle = 0 # kot pri naključni hoji
        self.size = 15 #velikost agenta
        self.color = color #barva agenta

    # Posodabljanje hitrosti (velocity) in pozicije (position) preverjamo če ima preveliko hitrost
    def update(self):
        self.velocity += self.acceleration
        if self.velocity.length() > self.max_speed:
            self.velocity.scale_to_length(self.max_speed)
        self.position += self.velocity
        self.acceleration *= 0

    # Dodajanje sile (force) na agentov pospešek (acceleration)
    def apply_force(self, force):
        self.acceleration += force

    # Trikotnik v smeri hitrosti (glava)
    def draw(self, screen):
        if not SIMULATION_RECT.collidepoint(self.position):
            return
        angle = math.atan2(self.velocity.y, self.velocity.x)
        heading = pygame.math.Vector2(math.cos(angle), math.sin(angle))
        p1 = self.position + heading * self.size
        p2 = self.position + heading.rotate(135) * self.size * 0.5
        p3 = self.position + heading.rotate(-135) * self.size * 0.5
        pygame.draw.polygon(screen, self.color, [p1, p2, p3])

    # 1. Isci in pristani (agenti proti kazalcu miške)
    def seek(self, target):
        desired = target - self.position
        distance = desired.length()
        if distance == 0: # agent je pri cilju
            return
        slowing_radius = 100
        if distance < slowing_radius: # če je agent blizu cilju, upočasni
            speed = self.max_speed * (distance / slowing_radius)
        else:
            speed = self.max_speed
        desired = desired.normalize() * speed
        steer = desired - self.velocity #usmeritvena sila
        if steer.length() > self.max_force:
            steer.scale_to_length(self.max_force)
        self.apply_force(steer)

    # 2. Nakljucna naravna hoja
    def wander(self):
        wander_radius = 50
        wander_distance = 80
        change = 0.3 # Kako mocno lahko spreminja smer
        self.wander_angle += random.uniform(-change, change) #nakljucno kot
        if self.velocity.length() == 0: #agent miruje ne usmerjamo naprej
            return
        circle_center = self.velocity.normalize() * wander_distance # sredisce kroga
        #izracunamo novo nakljucno tocko na krogu
        displacement = pygame.math.Vector2(wander_radius * math.cos(self.wander_angle),
                                           wander_radius * math.sin(self.wander_angle))
        wander_force = circle_center + displacement # koncna sila ki usmerja gibanje
        if wander_force.length() > self.max_force: # omeji silo ce premocna
            wander_force.scale_to_length(self.max_force)
        self.apply_force(wander_force)

    # 3. Gibanje v omejenem prostoru (ko pribliza robu ga nezno potisne nazaj proti sredini) margin notranji varnosti rob
    def stay_in_bounds(self, margin=20):
        # neviden okvir okoli simulacije
        left = SIMULATION_RECT.left + margin
        right = SIMULATION_RECT.right - margin
        top = SIMULATION_RECT.top + margin
        bottom = SIMULATION_RECT.bottom - margin
        steer = pygame.math.Vector2(0, 0) # sila ki potiska nazaj
        # Preverimo na katerem robu zapusca prostor in dodamo silo v tisto smer
        if self.position.x < left:
            steer += pygame.math.Vector2(self.max_speed, 0)
        elif self.position.x > right:
            steer += pygame.math.Vector2(-self.max_speed, 0)
        if self.position.y < top:
            steer += pygame.math.Vector2(0, self.max_speed)
        elif self.position.y > bottom:
            steer += pygame.math.Vector2(0, -self.max_speed)
        if steer.length() > 0: # ce morali popraviti silo
            if steer.length() > self.max_force: # omejimo silo
                steer.scale_to_length(self.max_force)
            steer *= 2 # povečamo silo
            self.apply_force(steer)

    # 4. Ločitev (agent se odmakne od drugih agentov svoje jate) desired_separation -  minimalno varnostno razdaljo med agenti
    def separate(self, agents, desired_separation=35):
        steer = pygame.math.Vector2(0, 0) # vektor za smer umika
        total = 0 # stevec angeotv ki preblizu
        for other in agents: # preverimo vse agente
            if other == self:
                continue
            distance = self.position.distance_to(other.position)
            # ce je drug agent preblizu izracunamo smer umika
            if 0 < distance < desired_separation:
                diff = self.position - other.position
                diff = diff.normalize() / distance
                steer += diff
                total += 1
        if total > 0: # vec kot 1 agent preblizu
            steer /= total
            if steer.length() > 0:
                steer = steer.normalize() * self.max_speed #prilagodimo hitrost
                steer -= self.velocity
                if steer.length() > self.max_force:
                    steer.scale_to_length(self.max_force)
                self.apply_force(steer)

    # 5. Poravnava (agent se poravna s hitrostjo drugih agentov) neighbor_dist - radij kjer upotevamo druge agente kot svoje sosede
    def align(self, agents, neighbor_dist=70):
        sum_velocity = pygame.math.Vector2(0, 0) # sum hitrosti sosedov
        total = 0 # koliko sosedov imamo
        for other in agents:
            if other == self:
                continue
            distance = self.position.distance_to(other.position) # razdalja do drugega agenta
            if distance < neighbor_dist:
                sum_velocity += other.velocity # dodamo hitrost drugega agenta
                total += 1
        if total > 0:
            average = sum_velocity / total # povprecna hitrost
            average = average.normalize() * self.max_speed # prilagodimo hitrost
            steer = average - self.velocity # izracunamo krmilno silo
            if steer.length() > self.max_force:
                steer.scale_to_length(self.max_force) # omejimo silo
            self.apply_force(steer)

    # 6. Kohezija (agent se premika proti sredini svoje jate) neighbor_dist - radij kjer upotevamo druge agente kot svoje sosede
    def cohesion(self, agents, neighbor_dist=80):
        center_mass = pygame.math.Vector2(0, 0) # sredisce mase
        total = 0 # koliko sosedov imamo
        for other in agents:
            if other == self:
                continue
            distance = self.position.distance_to(other.position)
            if distance < neighbor_dist: # ce je drug agent v radiju v blizini
                center_mass += other.position # dodamo pozicijo drugega agenta
                total += 1
        if total > 0:
            center_mass /= total # povprecje mase
            self.seek(center_mass) # priblizamo se srediscu mase

    # 7. Jata (kombinacija ločitve, poravnave in kohezije)
    def flock(self, agents):
        self.separate(agents)
        self.align(agents)
        self.cohesion(agents)

    # 8. Ovire (agent se izogiba oviram) avoid_radius - radij kjer upostevamo ovire
    def avoid_obstacles(self, obstacles, avoid_radius=60):
        steer = pygame.math.Vector2(0, 0) # sila izogibanja
        total = 0 # koliko ovir imamo
        for obs in obstacles:
            distance = self.position.distance_to(obs.position) # razdalja do ovire
            if distance < obs.radius + avoid_radius: # ce je ovira v radiju (agent preblizu ovire)
                diff = self.position - obs.position # izracunamo vektor od ovire do agenta
                if diff.length() > 0:
                    diff = diff.normalize() / distance # Manjša kot je razdalja, večja je sila
                    steer += diff
                    total += 1
        if total > 0:
            steer /= total # povprecje sile
            if steer.length() > 0:
                steer = steer.normalize() * self.max_speed # prilagodimo hitrost
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

    # Resetiranje simulacije in gumbov
    if RESET_SIMULATION[0]:
        flock1 = create_flock1()
        flock2 = create_flock2()
        for toggle in [USE_SEEK, USE_WANDER, USE_BOUNDS, USE_SEPARATION, USE_ALIGNMENT, USE_COHESION, USE_FLOCK, USE_AVOID]:
            toggle[0] = False
        RESET_SIMULATION[0] = False

    mouse_vector = pygame.math.Vector2(pygame.mouse.get_pos())

    for flock in [flock1, flock2]:
        for agent in flock:
            if USE_SEEK[0]: agent.seek(mouse_vector) # 1. Isci in pristani
            if USE_FLOCK[0]: agent.flock(flock) # 7. Jata
            else:
                if USE_SEPARATION[0]: agent.separate(flock) # 4. Ločitev
                if USE_ALIGNMENT[0]: agent.align(flock) # 5. Poravnava
                if USE_COHESION[0]: agent.cohesion(flock) # 6. Kohezija
            if USE_WANDER[0]: agent.wander() # 2. Nakljucna hoja
            if USE_AVOID[0]: agent.avoid_obstacles(obstacles) # 8. Ovire

            if USE_BOUNDS[0]: agent.stay_in_bounds() # 3. Omejen prostor
            agent.update()
            agent.draw(screen)

    for obstacle in obstacles:
        if SIMULATION_RECT.collidepoint(obstacle.position):
            obstacle.draw(screen)

    for button in buttons:
        button.draw(screen, font)

    pygame.display.flip()
    clock.tick(120)

pygame.quit()
