import tkinter as tk
import random
import time
from datetime import datetime
from PIL import Image, ImageTk, ImageChops
from pynput import keyboard
import pyautogui
import os
import threading

# Set the AFK timeout to 1 hour (3600 seconds)
AFK_TIMEOUT = 3600
BRING_SOMETHING_INTERVAL = 5 * 60  # 5 minutes


class DesktopPet:
    def __init__(self):
        self.window = tk.Tk()

        # AFK checking variables
        self.last_mouse_position = pyautogui.position()
        self.last_activity_time = time.time()
        self.is_afk = False

        self.last_move_time = time.time()
        self.last_bring_time = time.time()

        self.teleport_interval = 20 * 60  # 20 minutes

        # Get screen dimensions
        self.screen_width = self.window.winfo_screenwidth()
        self.screen_height = self.window.winfo_screenheight()

        # Initial position
        self.x = self.screen_width // 2
        self.y = self.screen_height // 2
        self.initial_x = self.x
        self.initial_y = self.y

        self.window.geometry(f'100x100+{self.x}+{self.y}')
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        self.window.configure(bg='black')
        self.window.wm_attributes('-transparentcolor', 'black')

        # State variables
        self.current_state = 'idle'
        self.frame_index = 0
        self.dragging = False
        self.drag_x = 0
        self.drag_y = 0
        self.target_x = self.x
        self.target_y = self.y

        # Define animation states and their properties
        self.states = {
            'idle': {'file': 'idle.gif', 'delay': 400},
            'sleep': {'file': 'sleep.gif', 'delay': 1000},
            'walk_left': {'file': 'walk_left.gif', 'delay': 100},
            'walk_right': {'file': 'walk_right.gif', 'delay': 100},
            'afk': {'file': 'afk.gif', 'delay': 1000}  # Add AFK state
        }

        # Load images and calculate offsets
        self.images = {}
        self.image_offsets = {}
        self.load_images()

        # Create label for displaying images
        self.label = tk.Label(self.window, bd=0, bg='black')
        self.label.pack()

        # Bind mouse events
        self.label.bind('<Button-1>', self.on_click)
        self.label.bind('<B1-Motion>', self.drag)
        self.label.bind('<ButtonRelease-1>', self.stop_drag)
        self.label.bind('<Button-3>', self.show_menu)

        # Create context menu
        self.menu = tk.Menu(self.window, tearoff=0)
        self.menu.add_command(label="Reset Position", command=self.reset_position)
        self.menu.add_command(label="Play osu!", command=self.play_osu)  # Add Play osu! option
        self.menu.add_command(label="Teleport Pointer", command=self.teleport_pointer)  # Add Teleport Pointer option
        self.menu.add_command(label="Exit", command=self.window.quit)

        # Start animation and AFK checking
        self.check_afk()
        self.animate()

        # Start the keyboard listener in a separate thread
        listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        listener.start()

        # Start the movement and sleep logic in a separate thread
        threading.Thread(target=self.enforce_movement_and_sleep).start()

    def load_images(self):
        image_path = 'C:\\Users\\user\\Desktop\\Project\\image\\'  # Update this path
        try:
            for state, props in self.states.items():
                self.images[state] = []
                filename = props['file']
                full_path = os.path.join(image_path, filename)
                print(f"Loading image: {full_path}")  # Debug information
                if os.path.exists(full_path):
                    image = Image.open(full_path)
                    offsets = self.calculate_offsets(image)
                    self.image_offsets[state] = offsets
                    for frame in range(image.n_frames):
                        image.seek(frame)
                        frame_image = ImageTk.PhotoImage(image.copy())
                        self.images[state].append(frame_image)
                else:
                    print(f"File not found: {full_path}.")
        except Exception as e:
            print(f"Error loading images: {e}")
            self.window.destroy()
            exit()

    def calculate_offsets(self, image):
        """
        Calculate the offsets to center the visible part of the image over the pointer.
        """
        bbox = ImageChops.difference(image, Image.new(image.mode, image.size)).getbbox()
        if bbox:
            left, upper, right, lower = bbox
            offset_x = (image.width - (right - left)) // 2
            offset_y = (image.height - (lower - upper)) // 2
            return offset_x, offset_y
        return 0, 0

    def check_afk(self):
        current_mouse_position = pyautogui.position()

        # Check if mouse has moved
        if current_mouse_position != self.last_mouse_position:
            self.last_activity_time = time.time()
            self.last_mouse_position = current_mouse_position
            if self.is_afk:
                print("User has returned!")
                self.is_afk = False
                self.current_state = 'idle'

        # Check if AFK
        if time.time() - self.last_activity_time > AFK_TIMEOUT and not self.is_afk:
            print("User is AFK!")
            self.is_afk = True
            self.current_state = 'sleep'
            self.frame_index = 0

        # Schedule next check
        self.window.after(100, self.check_afk)

    def on_press(self, key):
        try:
            print(f"Key {key.char} pressed")
        except AttributeError:
            print(f"Special key {key} pressed")
        # Reset the AFK timer on any key press
        self.last_activity_time = time.time()
        if self.is_afk:
            self.is_afk = False
            self.current_state = 'idle'

    def on_release(self, key):
        print(f"Key {key} released")
        # If the Escape key is pressed, stop the listener
        if key == keyboard.Key.esc:
            return False

    def on_click(self, event):
        # Start dragging after a delay to distinguish between click and drag
        self.label.after(200, lambda: self.start_drag(event))

    def start_drag(self, event):
        if not self.dragging:
            self.dragging = True
            self.drag_x = event.x
            self.drag_y = event.y
            self.last_activity_time = time.time()  # Reset AFK timer on drag
            self.current_state = 'walk_right' if random.random() < 0.5 else 'walk_left'

    def drag(self, event):
        if self.dragging:
            # Center the cat around the mouse pointer
            offset_x, offset_y = self.image_offsets[self.current_state]
            new_x = event.x_root - offset_x
            new_y = event.y_root - offset_y

            new_x = max(0, min(new_x, self.screen_width - 100))
            new_y = max(0, min(new_y, self.screen_height - 100))

            self.x = new_x
            self.y = new_y
            self.window.geometry(f'100x100+{int(self.x)}+{int(self.y)}')  # Convert to int

            # Update animation frame while dragging
            self.frame_index = (self.frame_index + 1) % len(self.images[self.current_state])
            self.label.configure(image=self.images[self.current_state][self.frame_index])

    def stop_drag(self, event):
        self.dragging = False
        self.last_move_time = time.time()  # Reset last move time

    def show_menu(self, event):
        self.menu.post(event.x_root, event.y_root)
        self.last_activity_time = time.time()  # Reset AFK timer on menu interaction

    def reset_position(self):
        self.move_to(self.initial_x, self.initial_y, duration=3.0)

    def change_state(self):
        # Get the current hour
        current_hour = datetime.now().hour

        if current_hour >= 22 or self.is_afk:
            self.current_state = 'sleep'
        else:
            if not self.dragging:
                possible_states = ['idle', 'sleep', 'walk_left', 'walk_right']
                self.current_state = random.choice(possible_states)
                self.frame_index = 0

                if self.current_state == 'walk_left':
                    self.target_x = random.randint(0, self.screen_width // 2)
                elif self.current_state == 'walk_right':
                    self.target_x = random.randint(self.screen_width // 2, self.screen_width - 100)
                self.target_y = random.randint(0, self.screen_height - 100)

    def animate(self):
        if not self.dragging:
            self.frame_index = (self.frame_index + 1) % len(self.images[self.current_state])
            self.label.configure(image=self.images[self.current_state][self.frame_index])

            # Move towards the target position if in walk state
            if self.current_state in ['walk_left', 'walk_right']:
                if self.x < self.target_x:
                    self.x += 1
                elif self.x > self.target_x:
                    self.x -= 1
                if self.y < self.target_y:
                    self.y += 1
                elif self.y > self.target_y:
                    self.y -= 1

                if self.x == self.target_x and self.y == self.target_y:
                    self.current_state = 'idle'  # Stop walking when target is reached

            # Randomly move to a new position and then return to the initial position
            if not self.is_afk and random.random() < 0.01:
                self.move_to_random_position()

            self.window.geometry(f'100x100+{int(self.x)}+{int(self.y)}')  # Convert to int

        self.window.after(self.states[self.current_state]['delay'], self.animate)

    def move_to_random_position(self):
        # Randomly choose left or right side of the screen
        if random.random() < 0.5:
            new_x = random.randint(0, self.screen_width // 4)
            self.current_state = 'walk_left'
        else:
            new_x = random.randint((self.screen_width * 3) // 4, self.screen_width - 100)
            self.current_state = 'walk_right'
        new_y = random.randint(0, self.screen_height - 100)
        self.move_to(new_x, new_y, duration=3.0)

        # Simulate bringing back a file
        self.window.after(3000, self.bring_back_file)

    def bring_back_file(self):
        # Choose a random file (text or image) to "bring back"
        if random.random() < 0.5:
            self.bring_back_text_file()
        else:
            self.bring_back_image()

    def bring_back_text_file(self):
        # Choose a random text file to "bring back"
        file_number = random.randint(1, 10)
        file_name = f"text{file_number}.txt"
        file_path = os.path.join('C:\\Users\\user\\Desktop\\Project\\image\\', file_name)

        # Create the text file if it doesn't exist
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                f.write(f"This is the content of {file_name}")

        self.open_text_file(file_path)

        # Return to the initial position
        self.move_to(self.initial_x, self.initial_y, duration=3.0)

    def open_text_file(self, file_path):
        text_window = tk.Toplevel(self.window)
        text_window.title(f"Brought Back {os.path.basename(file_path)}")
        text_window.overrideredirect(True)  # Make the window borderless
        text_area = tk.Text(text_window, wrap='word', bg='white', fg='black', font=('Arial', 12))
        text_area.pack(expand=1, fill='both')

        with open(file_path, 'r') as f:
            content = f.read()

        text_area.insert('1.0', content)
        text_area.config(state='disabled')

        # Make the window intangible
        text_window.attributes("-transparentcolor", "white")
        text_area.bind("<Button-3>", lambda event: self.show_close_menu(event, text_window))

        # Move the window to the outskirts and then bring it inside
        self.animate_window_movement(text_window, file_path)

    def bring_back_image(self):
        # Choose a random image file to "bring back"
        file_number = random.randint(1, 10)
        file_name = f"image{file_number}.png"
        file_path = os.path.join('C:\\Users\\user\\Desktop\\Project\\image\\', file_name)

        # Create a sample image if it doesn't exist
        if not os.path.exists(file_path):
            img = Image.new('RGB', (100, 100), color='red')
            img.save(file_path)

        self.open_image_file(file_path)

        # Return to the initial position
        self.move_to(self.initial_x, self.initial_y, duration=3.0)

    def open_image_file(self, file_path):
        image_window = tk.Toplevel(self.window)
        image_window.title(f"Brought Back {os.path.basename(file_path)}")
        image_window.overrideredirect(True)  # Make the window borderless
        img = Image.open(file_path)
        img = ImageTk.PhotoImage(img)
        lbl = tk.Label(image_window, image=img)
        lbl.image = img
        lbl.pack()

        # Make the window intangible
        image_window.attributes("-transparentcolor", "white")
        lbl.bind("<Button-3>", lambda event: self.show_close_menu(event, image_window))

        # Move the window to the outskirts and then bring it inside
        self.animate_window_movement(image_window, file_path)

    def animate_window_movement(self, window, file_path):
        # Start at a random position off the screen
        start_x = random.choice([-100, self.screen_width + 100])
        start_y = random.randint(-100, self.screen_height + 100)
        window.geometry(f'100x100+{start_x}+{start_y}')
        window.update()

        # Move the window to a random position on the screen
        target_x = random.randint(0, self.screen_width - 100)
        target_y = random.randint(0, self.screen_height - 100)

        steps = 100
        delta_x = (target_x - start_x) / steps
        delta_y = (target_y - start_y) / steps

        for _ in range(steps):
            start_x += delta_x
            start_y += delta_y
            window.geometry(f'100x100+{int(start_x)}+{int(start_y)}')
            window.update()
            time.sleep(0.01)

    def show_close_menu(self, event, window):
        menu = tk.Menu(self.window, tearoff=0)
        menu.add_command(label="Close", command=window.destroy)
        menu.post(event.x_root, event.y_root)

    def move_to(self, target_x, target_y, duration=3.0):
        # Determine direction
        if target_x > self.x:
            self.current_state = 'walk_right'
        else:
            self.current_state = 'walk_left'

        steps = int(duration * 20)  # 20 updates per second
        delta_x = (target_x - self.x) / steps
        delta_y = (target_y - self.y) / steps

        for _ in range(steps):
            self.x += delta_x
            self.y += delta_y
            self.window.geometry(f'100x100+{int(self.x)}+{int(self.y)}')  # Convert to int

            # Update animation frame while moving
            self.frame_index = (self.frame_index + 1) % len(self.images[self.current_state])
            self.label.configure(image=self.images[self.current_state][self.frame_index])
            self.window.update()
            time.sleep(duration / steps)

    def teleport_pointer(self):
        """Teleport the mouse pointer to a new position."""
        new_x = random.randint(0, self.screen_width)
        new_y = random.randint(0, self.screen_height)
        pyautogui.moveTo(new_x, new_y)
        self.last_move_time = time.time()  # Reset last move time

    def enforce_movement_and_sleep(self):
        while True:
            try:
                current_time = time.time()
                if current_time - self.last_move_time > 300:  # 5 minutes
                    self.move_to_random_position()
                elif current_time - self.last_move_time > 60:  # 1 minute
                    self.current_state = 'sleep'

                if current_time - self.last_bring_time > BRING_SOMETHING_INTERVAL:
                    self.bring_back_file()
                    self.last_bring_time = time.time()
            except Exception as e:
                print(f"Error in enforce_movement_and_sleep: {e}")
            time.sleep(1)

    def play_osu(self):
        """Launch osu! game within the same window."""
        osu_game = OsuGame()
        osu_game.run()

class OsuGame:
    def __init__(self):
        self.window = tk.Toplevel()
        self.window.title("Simple Osu! Game")
        self.window.geometry("800x600")
        self.canvas = tk.Canvas(self.window, width=800, height=600, bg='black')
        self.canvas.pack()

        self.score = 0
        self.circle = None
        self.circle_radius = 30
        self.game_over = False
        self.spawn_interval = 3000  # Initial spawn interval in milliseconds

        self.score_label = tk.Label(self.window, text=f"Score: {self.score}", fg="white", bg="black", font=("Helvetica", 16))
        self.score_label.pack()

        self.window.bind("<Button-1>", self.check_hit)
        self.spawn_circle()

    def spawn_circle(self):
        if self.game_over:
            return

        if self.circle:
            self.canvas.delete(self.circle)
            self.game_over = True
            self.show_game_over()
            return

        x = random.randint(self.circle_radius, 800 - self.circle_radius)
        y = random.randint(self.circle_radius, 600 - self.circle_radius)
        self.circle = self.canvas.create_oval(x - self.circle_radius, y - self.circle_radius,
                                              x + self.circle_radius, y + self.circle_radius,
                                              fill='red', outline='white')
        self.window.after(self.spawn_interval, self.spawn_circle)

    def check_hit(self, event):
        if self.game_over:
            return

        x, y = event.x, event.y
        if self.circle:
            coords = self.canvas.coords(self.circle)
            circle_x = (coords[0] + coords[2]) / 2
            circle_y = (coords[1] + coords[3]) / 2
            if (x - circle_x) ** 2 + (y - circle_y) ** 2 <= self.circle_radius ** 2:
                self.score += 1
                self.score_label.config(text=f"Score: {self.score}")
                print(f"Hit! Score: {self.score}")
                self.canvas.delete(self.circle)
                self.circle = None
                self.adjust_difficulty()  # Increase difficulty as score increases
            else:
                self.game_over = True
                self.show_game_over()
        else:
            self.game_over = True
            self.show_game_over()

    def adjust_difficulty(self):
        # Decrease the spawn interval to make the game progressively harder
        self.spawn_interval = max(500, 3000 - (self.score * 100))

    def show_game_over(self):
        self.canvas.create_text(400, 300, text="Game Over", fill="white", font=("Helvetica", 32))
        self.canvas.create_text(400, 350, text=f"Final Score: {self.score}", fill="white", font=("Helvetica", 24))

    def run(self):
        self.window.mainloop()
if __name__ == "__main__":
    pet = DesktopPet()
    pet.window.mainloop()