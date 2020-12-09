## ConsoleMe UI Setup

### Prerequisites

- [Semantic UI React](https://react.semantic-ui.com/)
- [React Hooks](https://reactjs.org/docs/hooks-intro.html)
- Single Page Application
- Linters (ESLint, Prettier)

### Notes

- ConsoleMe UI is a SPA (Single Page Application).
- Page Components are protected by `auth/ProtectedRoute.js` and requires authentication via `auth/AuthProviderDefault.js`.
- ConsoleMe UI components are currently written in both Classes and Hooks. We will move to React Hooks entirely over time.
- The react-app-wired module is used to start/build because of [Monaco Editor](https://microsoft.github.io/monaco-editor/). This was required due to how Monaco Editor was written.

## Available Scripts

In this directory, you can run:

### `yarn start`

Runs the app in the development mode.<br />
Open [http://localhost:3000](http://localhost:3000) to view it in the browser. (You should also run the ConsoleMe Python backend to see data)

ConsoleMe UI uses `proxy` in `package.json` file to proxy api backend requests to [http://localhost:8081](http://localhost:8081) for local development.

### `yarn build:prod`

Builds the app for production to the `build` folder.<br />
It correctly bundles React in production mode and optimizes the build for the best performance.

The build is minified and the filenames include the hashes.<br />

Once the build is done, it copies the files in build directory to ../consoleme/templates directory to package them with backend code.
You can locally test this by accessing `http://localhost:8081` to see the actual build output served from ConsoleMe Tornado server.

### `yarn lint` and `yarn lint:fix`

Please run this before submitting a PR. This will run prettier linter against to the `src` directory. `yarn lint:fix` will fix lint errors. This lint is moved out of eslintrc to reduce distraction.
