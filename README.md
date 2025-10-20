# USB 16-Channel Relay Control App V1.0
## Board Screenshot
![Board Screenshot](https://github.com/peterpt/USB-Relay-Control/blob/main/board.png)


## APP Screenshot
![App Screenshot](https://github.com/peterpt/USB-Relay-Control/blob/main/app.png)

## Description

This Python application provides a graphical user interface (GUI) to control a specific 16-channel USB relay board based on the **QinHeng Electronics CH340 serial converter (ID 1a86:7523)**.

After an extensive reverse-engineering process, the specific command protocol for this board was identified, and this application was built to provide a stable, user-friendly, and cross-platform (Windows/Linux) control panel for it.

The project was a collaboration between the user and the Google AI Gemini.

## Features

*   **Auto-Detection:** Automatically scans and detects compatible USB relay boards by their specific hardware ID.
*   **Multi-Device Support:** Configure and switch between multiple connected relay boards.
*   **Persistent Configuration:** Saves device nicknames and custom relay labels to an `.ini` file.
*   **Customizable Interface:**
    *   Assign custom names to each of the 16 relays (e.g., "Main Lights", "Engine Pump").
    *   Assign custom ON/OFF icons for each relay from an `icons` folder.
*   **Live Connection Monitoring:** The GUI visually indicates if the selected board becomes disconnected and disables controls to prevent errors.
*   **Cross-Platform:** Works on both Windows and Linux systems.

## Requirements

*   **Python 3.x**
*   **PySerial:** `pip install pyserial`
*   **Pillow (PIL Fork):** `pip install Pillow`
*   A compatible 16-channel USB relay board with the **CH340 (1a86:7523)** chipset.

## Hardware Command Protocol

The application controls the board by sending specific 17-byte hexadecimal commands over the serial port at a **9600 baud rate**. The protocol was discovered to be an ASCII-HEX format.

*   **Example Command (Relay 1 ON):** `3A 46 45 30 35 30 30 30 30 46 46 30 30 46 45 0D 0A`
*   **Example Command (Relay 1 OFF):** `3A 46 45 30 35 30 30 30 30 30 30 30 30 46 44 0D 0A`

## How to Use

1.  **Clone or Download the Repository:**
    ```bash
    git clone https://github.com/peterpt/USB-Relay-Control.git
    cd USB-Relay-Control
    ```

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Connect the Hardware:**
    *   Ensure the relay board's blue jumper is in the **USB** position.
    *   Connect both the USB cable and the external 12V DC power supply.

4.  **Run the Application:**
    ```bash
    python3 gui.py
    ```

5.  **First-Time Setup:**
    *   Go to **Configure -> Devices...**.
    *   The application will scan for connected boards. Your board should appear as a **[New]** device.
    *   Select the new device and click **"Configure..."**.
    *   Give the module a nickname and assign custom labels to each of the 16 relays. Click **"Save"**.
    *   The main window will now display and control your newly configured board.

## License

This project is licensed under the MIT License
