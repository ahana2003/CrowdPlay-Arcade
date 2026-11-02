# CrowdPlay Arcade

A small stream overlay where Twitch chat can play three quick games together: Tic-Tac-Toe, Guess the Word, and Math Challenge. The project has a local demo so you can see complete rounds without a Twitch account. When configured, the same page reads commands from Twitch chat.

## Start it on Windows

1. Extract the downloaded ZIP to a normal folder (for example, Desktop\CrowdPlay Arcade).
2. Install Python 3.10 or newer from https://www.python.org/downloads/windows/ if it is not already installed. In the installer, enable **Add Python to PATH**.
3. Double-click **run.bat**. First launch installs the app's packages and can take a minute; internet is needed for that first setup.
4. Leave the black server window open. The browser opens only after the server health check succeeds. Open http://127.0.0.1:5055/ if it does not open automatically.
5. Click **Play sample round** to see a complete round of each game. To play yourself, click **Start random game**. In local mode, click empty Tic-Tac-Toe squares for a two-player game, click letters to reveal a word, or enter an answer to a math problem. For OBS, add a Browser Source with URL `http://127.0.0.1:5055/`.
6. Stop the app with Ctrl+C in the black server window.

The app binds to this computer only (`127.0.0.1`). It does not expose your local server to the internet.

## Connect Twitch chat

You need a Twitch account to connect real chat. No account is needed for the local demo. Do not send your password or token to anyone.

1. Sign in to Twitch and create a **separate bot account** for chat, or use your own Twitch account as the bot. The channel name is the broadcaster whose chat viewers will use; it can be your account or another channel you can access.
2. Register a Twitch application in the Twitch Developer Console: https://dev.twitch.tv/console/apps. Set OAuth Redirect URL to `http://localhost` and choose the appropriate application category.
3. Generate a user access token for the bot account with the `chat:read` scope using Twitch's official authorization flow. Keep the token private. It is not the Twitch password.
4. Stop the server (Ctrl+C). In the project folder, open `.env` with Notepad and set:

   - `TWITCH_CHANNEL=` the channel login, without `#` (for example, `yourchannel`)
   - `TWITCH_USERNAME=` the bot account's Twitch login
   - `TWITCH_TOKEN=` the bot access token

5. Save `.env`, run **run.bat** again, and wait for the top status to say **TWITCH CHAT CONNECTED**. If it reports a login error, stop the server and check the username, token, and `chat:read` permission.
6. Start a game, then type the command shown on screen in the Twitch channel's chat. Commands are `!join` and `!move 1` through `!move 9` for Tic-Tac-Toe, `!letter <letter>` or `!word <answer>` for Guess the Word, and `!answer <number>` for Math Challenge. Type `!arcade` to start a random game.

This app uses Twitch IRC chat and does not currently use EventSub or the Twitch API. Confirm the event's current rules before claiming a particular integration in your submission.

## Troubleshooting

- If the page says **SERVER OFFLINE**, keep `run.bat` open and check its error text. The browser page polls the server and will recover after you restart it.
- If Python is not found, install Python 3.10+ and check **Add Python to PATH**, then reopen the folder and run `run.bat`.
- If port 5055 is already occupied, close the other local server or change `PORT=5055` in `.env` to another free port, then visit that port in the browser.
- `.env` contains a private token and is intentionally not included in the ZIP. Never publish it in a repository or screenshot.


