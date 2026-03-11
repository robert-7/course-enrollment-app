# Testing

Assuming was started correctly, when implementing changes, here is an end-to-end
test-case for assessing whether everything works:

1. Follow the steps in [CONTRIBUTING.md](CONTRIBUTING.md), then bring up the environment with `docker compose up -d --build`.
1. Go to [home page](http://127.0.0.1:5000/index). The web page should load.
1. Go to [the courses page](http://127.0.0.1:5000/courses).
   The web page should load and show 5 courses.
1. Go to [the registration page](http://127.0.0.1:5000/register).
   The web page should load with a form.
1. Fill in the form with some data, and hit "Register Now".
   You should be redirected to the [home page](http://127.0.0.1:5000/index).
1. Go to [the login page](http://127.0.0.1:5000/login).
   The web page should load with a login form.
1. Fill in the form with the data from earlier, and hit "Login".
   You should be redirected to the [home page](http://127.0.0.1:5000/index).
   You should also see the `Register` and `Login` navigation buttons have disappeared.
1. Go to [the courses page](http://127.0.0.1:5000/courses) and click "Enroll" for a course.
   You should be redirected to the [the enrollment page](http://127.0.0.1:5000/enrollment).
1. Click the `Logout` navigation button and you should be logged out.

## Automated E2E walkthrough (Playwright)

The repository includes an automated UI walkthrough that mirrors the manual
flow above.

### One-time setup

```bash
npm install
npx playwright install chromium
```

### Run the app (Docker)

```bash
docker compose up -d --build
```

### Run the automated walkthrough

```bash
npm run e2e:walkthrough
```

For a viewer-friendly recording pace, use slow motion:

```bash
npm run e2e:walkthrough:demo
```

This executes [e2e/ui-walkthrough.spec.js](e2e/ui-walkthrough.spec.js) against
`http://127.0.0.1:5000`.

### Other useful commands

- `npm run e2e` : all Playwright tests (headless)
- `npm run e2e:headed` : all Playwright tests (headed)
- `npm run e2e:report` : open HTML test report
- `npm run e2e:walkthrough:demo` : walkthrough with `PW_SLOWMO=400` for demos

### Artifacts and GIF export

Playwright outputs video and trace artifacts under `test-results/`.

Convert the generated `.webm` video to GIF:

```bash
ffmpeg -i test-results/<run-folder>/video.webm \
   -vf "fps=12,scale=1200:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" \
   walkthrough.gif
```

If a recorded video still feels fast, slow playback during conversion:

```bash
ffmpeg -i test-results/<run-folder>/video.webm \
   -vf "setpts=1.4*PTS,fps=12,scale=1200:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" \
   walkthrough-slower.gif
```
