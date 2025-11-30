# main.py
import pygame
import json
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, BLACK
from agent import Agent, AIKnowledge
from world import WorldMap
from ui import UI

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("AI Survival - 180 Days (Refactored)")
        self.clock = pygame.time.Clock()
        self.ui = UI(self.screen)

        self.knowledge = AIKnowledge()
        try:
            self.knowledge.load_from_file()
        except json.JSONDecodeError as e:
            print(f"Błąd wczytywania pliku wiedzy (JSONDecodeError): {e}. Rozpoczynam bez danych historycznych.")
            self.knowledge = AIKnowledge()

        self.agent = None
        self.world_map = None
        self.running = True
        self.paused = False

        self.log = []
        self.max_log = 8

        self.simulation_active = False
        self.action_cooldown = 0
        self.action_delay = 1.0

    def start_new_attempt(self):
        self.world_map = WorldMap()
        self.agent = Agent(self.knowledge, self.world_map, self.add_log)
        self.log = []
        self.add_log(f"=== PRÓBA #{self.knowledge.attempts + 1} ===")
        self.add_log(f"Rekord: {self.knowledge.best_survival_days}/180 dni")
        self.simulation_active = True
        self.action_cooldown = 0

    def add_log(self, message):
        self.log.insert(0, message)
        if len(self.log) > self.max_log:
            self.log.pop()

    def simulate_tick(self, delta_time):
        if not self.agent or not self.agent.alive:
            return

        self.agent.update(delta_time, self.world_map)
        for enemy in self.world_map.enemies:
            enemy.update(delta_time, self.agent, self.world_map)

        self.action_cooldown -= delta_time
        if self.action_cooldown <= 0 and self.agent.stamina > 5 and self.agent.alive:
            action = self.agent.ai_decide_action(self.world_map)
            success, result, new_delay = self.agent.execute_action(action, self.world_map)

            if success and "Powrót" not in result and "Szukanie" not in result and "Eksploracja" not in result:
                self.add_log(f"[D{self.agent.current_day+1}] {result}")

            if new_delay is None or new_delay <= 0:
                new_delay = 0.1
            self.action_cooldown = new_delay

        if not self.agent.alive:
            self.end_attempt()
        elif self.agent.current_day >= 180:
            self.add_log("PRZEŻYTO 180 DNI!")
            self.simulation_active = False
            self.knowledge.save_to_file()

    def end_attempt(self):
        if self.agent:
            self.knowledge.record_death(self.agent.current_day, self.agent.death_cause)
            self.knowledge.save_to_file()
            self.add_log(f"💀 Przyczyna: {self.agent.death_cause}")
            self.add_log(f"Przeżyto: {self.agent.current_day}/180 dni")
        self.simulation_active = False

    def draw(self):
        self.screen.fill(BLACK)
        if not self.agent:
            self.ui.draw_menu(self.knowledge)
        else:
            self.ui.draw_game(self.agent, self.world_map, self.log, self.paused, self.simulation_active)
        pygame.display.flip()

    def run(self):
        while self.running:
            delta_time = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_pos = pygame.mouse.get_pos()
                    if not self.agent:
                        if mouse_pos[1] > SCREEN_HEIGHT - 300:
                            self.start_new_attempt()
                    else:
                        button_y = SCREEN_HEIGHT - 150
                        button_w = (SCREEN_WIDTH - 40) // 2
                        if 15 <= mouse_pos[0] <= 15 + button_w and button_y <= mouse_pos[1] <= button_y + 120:
                            self.paused = not self.paused
                        if 25 + button_w <= mouse_pos[0] <= 25 + button_w * 2 and button_y <= mouse_pos[1] <= button_y + 120:
                            if not self.simulation_active:
                                self.start_new_attempt()
            if self.simulation_active and not self.paused:
                self.simulate_tick(delta_time)
            self.draw()
        self.knowledge.save_to_file()
        pygame.quit()

if __name__ == "__main__":
    game = Game()
    game.run()
