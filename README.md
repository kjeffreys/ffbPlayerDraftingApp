
# Player Drafting App

## Description
A simple React application to draft players based on their positions. Users can filter players by position, view their names, teams, and Average Draft Positions (ADP), and pick them from the list. Players and ADP are currently in a static json list. If interested in quick use, feel free to edit the data.json locally or add more dynamic player queries from APIs.

## Features
- **Position Filter**: Easily filter players by positions like `QB`, `RB`, `WR`, `TE`, `K`, `DEF`, or a combined option `WR/RB`. Also, view all players without any filter.
- **Player List**: View players sorted by their ADP. Each player entry displays their name, team, and ADP.
- **Drafting**: Pick players directly from the list. Once a player is picked, they are removed from the available options.

## Installation and Setup
1. Clone the repository: `git clone [your-repository-link]`
2. Navigate to the project directory: `cd [your-project-directory-name]`
3. Install the dependencies: `npm install`
4. Run the application: `npm start`

## Project Structure
- `App.js`: Main application component.
- `PlayerList.js`: Component to display the list of players.
- `PositionSelector.js`: Dropdown component to filter players by position.
- `data.json`: Contains the list of players with their details.
- `App.css`: Main styling for the application.

## Usage
1. Use the position selector dropdown to filter players by position.
2. Browse the list of players and pick your desired ones by clicking on the "Pick" button.

# Getting Started with Create React App

This project was bootstrapped with [Create React App](https://github.com/facebook/create-react-app).

## Available Scripts

In the project directory, you can run:

### `npm start`

Runs the app in the development mode.\
Open [http://localhost:3000](http://localhost:3000) to view it in your browser.

The page will reload when you make changes.\
You may also see any lint errors in the console.

### `npm test`

Launches the test runner in the interactive watch mode.\
See the section about [running tests](https://facebook.github.io/create-react-app/docs/running-tests) for more information.

### `npm run build`

Builds the app for production to the `build` folder.\
It correctly bundles React in production mode and optimizes the build for the best performance.

The build is minified and the filenames include the hashes.\
Your app is ready to be deployed!

See the section about [deployment](https://facebook.github.io/create-react-app/docs/deployment) for more information.

### `npm run eject`

**Note: this is a one-way operation. Once you `eject`, you can't go back!**

If you aren't satisfied with the build tool and configuration choices, you can `eject` at any time. This command will remove the single build dependency from your project.

Instead, it will copy all the configuration files and the transitive dependencies (webpack, Babel, ESLint, etc) right into your project so you have full control over them. All of the commands except `eject` will still work, but they will point to the copied scripts so you can tweak them. At this point you're on your own.

You don't have to ever use `eject`. The curated feature set is suitable for small and middle deployments, and you shouldn't feel obligated to use this feature. However we understand that this tool wouldn't be useful if you couldn't customize it when you are ready for it.

## Learn More

You can learn more in the [Create React App documentation](https://facebook.github.io/create-react-app/docs/getting-started).

To learn React, check out the [React documentation](https://reactjs.org/).

### Code Splitting

This section has moved here: [https://facebook.github.io/create-react-app/docs/code-splitting](https://facebook.github.io/create-react-app/docs/code-splitting)

### Analyzing the Bundle Size

This section has moved here: [https://facebook.github.io/create-react-app/docs/analyzing-the-bundle-size](https://facebook.github.io/create-react-app/docs/analyzing-the-bundle-size)

### Making a Progressive Web App

This section has moved here: [https://facebook.github.io/create-react-app/docs/making-a-progressive-web-app](https://facebook.github.io/create-react-app/docs/making-a-progressive-web-app)

### Advanced Configuration

This section has moved here: [https://facebook.github.io/create-react-app/docs/advanced-configuration](https://facebook.github.io/create-react-app/docs/advanced-configuration)

### Deployment

This section has moved here: [https://facebook.github.io/create-react-app/docs/deployment](https://facebook.github.io/create-react-app/docs/deployment)

### `npm run build` fails to minify

This section has moved here: [https://facebook.github.io/create-react-app/docs/troubleshooting#npm-run-build-fails-to-minify](https://facebook.github.io/create-react-app/docs/troubleshooting#npm-run-build-fails-to-minify)
