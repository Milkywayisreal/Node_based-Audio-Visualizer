import pygame
from pygame.math import Vector2
import random
import math

# === Load amplitude data ===
with open("Audio/Output/amplitude.txt") as f:
    amplitude_list = [float(line.strip()) for line in f]

# === Audio Data  ===
SAMPLE_RATE = 22050
HOP_LENGTH = 512
DATA_FPS = SAMPLE_RATE / HOP_LENGTH  # ≈ 43.07

# === Display Config ===
WIDTH, HEIGHT = 600, 600
CENTER = Vector2(WIDTH // 2, HEIGHT // 2)
FPS = 60

# === Visual Settings ===
NUM_PARTICLES = 27
PARTICLE_RADIUS = 1
BASE_CONNECTION_DISTANCE = 75  # Or slightly more
AMPLITUDE_CONNECTION_MULTIPLIER = 180  # Scales based on beat
LINE_THICKNESS = 5

# === Star Settings ===
AMPLITUDE_THRESHOLD = 0.75
STAR_SPAWN_CHANCE = 0.4
STAR_LIFETIME = 20
STAR_RADIUS = 30
MAX_STARS = 4

# === Flash Circle Settings ===
FLASH_RADIUS_START = 7
FLASH_RADIUS_GROWTH = 10
FLASH_LIFETIME = 20
FLASH_COLOR = (255, 255, 255)
FLASH_AMPLITUDE_TRIGGER = 0.85
FLASH_SPAWN_COUNT = (-1, 1)

# === Setup ===
pygame.init()
pygame.mixer.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Amplitude Node Visualizer")
clock = pygame.time.Clock()

# === Load and Play Music ===
pygame.mixer.music.load("Audio/File/Music.mp3")
pygame.mixer.music.play()
start_time = pygame.time.get_ticks()

# === Flash Circle Class ===
class FlashCircle:
    def __init__(self, pos, radius=FLASH_RADIUS_START, growth=FLASH_RADIUS_GROWTH, lifetime=FLASH_LIFETIME):
        self.pos = Vector2(pos)
        self.radius = radius
        self.growth = growth
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.alpha = 255

    def update(self):
        self.lifetime -= 1
        self.radius += self.growth
        self.alpha = max(0, int(255 * (self.lifetime / self.max_lifetime)))

    def is_alive(self):
        return self.lifetime > 0

    def draw(self, surface):
        flash_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.circle(flash_surface, FLASH_COLOR + (self.alpha,), self.pos, self.radius)
        surface.blit(flash_surface, (0, 0))
        
# === Function to Get Non-Overlapping Spawn Position ===
def get_non_overlapping_spawn(min_dist=180, max_attempts=100):
    for _ in range(max_attempts):
        angle = random.uniform(0, 6 * math.pi)
        distance = random.uniform(50, 550)
        pos = CENTER + Vector2(math.cos(angle), math.sin(angle)) * distance
        if all(pos.distance_to(p) > min_dist for p in Particle.spawned_positions):
            Particle.spawned_positions.append(pos)
            return pos
        
        # Optional: Clear every 60 seconds or so
        if len(Particle.spawned_positions) > 500:
            Particle.spawned_positions.clear()
            
    return CENTER + Vector2(random.uniform(-600, 300), random.uniform(-450, 250))  # fallback

# === Particle Class ===
class Particle:
    spawned_positions = []

    def __init__(self):
        self.pos = get_non_overlapping_spawn()
        self.radius = PARTICLE_RADIUS
        self.color = (255, 255, 255)
        self.pulse_timer = 0
        self.velocity = Vector2(0, 0)

    def update(self, amplitude):
        direction_to_center = (CENTER - self.pos)
        distance = direction_to_center.length()
        
        # Apply velocity with damping
        self.pos += self.velocity
        self.velocity *= 0.95  # slow down over time

        if distance < 25:
            self.pos = get_non_overlapping_spawn()

        force_direction = direction_to_center.normalize()
        gravity_strength = 3.6 + amplitude * 0.3  # Experiment: 1.0 - 2.0 base
        pull_force = force_direction * gravity_strength
        self.pos += pull_force
        self.pos += Vector2(random.uniform(-1, 1), random.uniform(-1, 1))
        

        if amplitude > 0.85:
            # Gentle randomized impulse with easing
            gravity_strength *= -1
            noise = Vector2(random.uniform(-3, 3), random.uniform(-3, 3))
            direction = ((self.pos - CENTER).normalize() + noise * 0.2).normalize()
            direction = direction.normalize()

            intensity = min((amplitude - 0.75) * 10, 15)
            self.velocity += direction * intensity

            self.pulse_timer = 3  # cooldown to prevent constant push

        if self.pulse_timer > 0:
            self.pulse_timer -= 1
        else:
            self.radius = PARTICLE_RADIUS
            self.color = (200, 200, 200)

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, self.pos, self.radius)

# === Star Class ===
class Star:
    def __init__(self):
        angle = random.uniform(0, 15 * math.pi)
        radius = random.uniform(0, 360)
        offset = Vector2(math.cos(angle), math.sin(angle)) * radius
        self.pos = CENTER + offset
        self.lifetime = STAR_LIFETIME
        self.alpha = 255
        self.angle = random.uniform(0, 360)
        self.rotation_speed = random.uniform(-5, 5)
        direction = (CENTER - self.pos).normalize()
        self.velocity = direction * 1.0

    def update(self):
        self.lifetime -= 1
        self.alpha = max(0, int(255 * (self.lifetime / STAR_LIFETIME)))
        self.angle += self.rotation_speed
        self.pos += self.velocity

    def is_alive(self):
        return self.lifetime > 0

# === Initialize Particles and Stars ===
Particle.spawned_positions.clear()
particles = [Particle() for _ in range(NUM_PARTICLES)]
stars = []
flashes = []

# === Function to Draw Star ===
def draw_star(surface, star, radius, spike_count=5):
    points = []
    angle_step = 360 / (spike_count * 2)
    for i in range(spike_count * 2):
        angle_deg = star.angle + angle_step * i
        angle_rad = math.radians(angle_deg)
        r = radius if i % 2 == 0 else radius / 2
        x = star.pos.x + math.cos(angle_rad) * r
        y = star.pos.y + math.sin(angle_rad) * r
        points.append((x, y))

    star_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.polygon(star_surface, (255, 255, 255, star.alpha), points)
    surface.blit(star_surface, (0, 0))

# === Visualizer Draw Function ===
def draw_visualizer(amplitude):
    screen.fill((15, 15, 20))

    for p in particles:
        p.update(amplitude)
        p.draw(screen)

    connection_distance = BASE_CONNECTION_DISTANCE + amplitude * AMPLITUDE_CONNECTION_MULTIPLIER
    max_connections = 45
    connections_drawn = 0

    for i, p1 in enumerate(particles):
        for p2 in particles[i + 1:]:
            if connections_drawn >= max_connections:
                break
            distance = p1.pos.distance_to(p2.pos)
            if distance < connection_distance:
                if distance < connection_distance * 0.4:
                    pygame.draw.line(screen, (255, 255, 255), p1.pos, p2.pos, LINE_THICKNESS * 2)
                else:
                    pygame.draw.line(screen, (69, 69, 69), p1.pos, p2.pos, LINE_THICKNESS)
                connections_drawn += 1

    if amplitude > AMPLITUDE_THRESHOLD and random.random() < STAR_SPAWN_CHANCE:
        if len(stars) < MAX_STARS:
            stars.append(Star())

    if amplitude > FLASH_AMPLITUDE_TRIGGER:
        for _ in range(random.randint(*FLASH_SPAWN_COUNT)):
            flashes.append(FlashCircle(
                pos=Vector2(random.randint(0, WIDTH), random.randint(0, HEIGHT)),
                radius=random.randint(5, 15),
                growth=random.uniform(1.5, 3.5),
                lifetime=random.randint(15, 35)
            ))

    for star in stars:
        star.update()
        if star.alpha > 0:
            draw_star(screen, star, STAR_RADIUS, spike_count=5)

    for flash in flashes:
        flash.update()
        flash.draw(screen)

    flashes[:] = [f for f in flashes if f.is_alive()]
    stars[:] = [s for s in stars if s.is_alive()]

# === Main Loop ===
running = True
while running:
    clock.tick(FPS)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    elapsed_ms = pygame.time.get_ticks() - start_time
    frame = int((elapsed_ms / 1000) * DATA_FPS)

    if frame < len(amplitude_list):
        amplitude = amplitude_list[frame]
        draw_visualizer(amplitude)
    else:
        running = False

    pygame.display.flip()

pygame.quit()
