document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const signupContainer = document.getElementById("signup-container");
  const messageDiv = document.getElementById("message");
  const userMenuButton = document.getElementById("user-menu-button");
  const userMenu = document.getElementById("user-menu");
  const authStatus = document.getElementById("auth-status");
  const loginButton = document.getElementById("login-button");
  const logoutButton = document.getElementById("logout-button");
  const loginDialog = document.getElementById("login-dialog");
  const loginForm = document.getElementById("login-form");
  let isTeacher = false;

  function showMessage(message, type) {
    messageDiv.textContent = message;
    messageDiv.className = `message ${type}`;
    setTimeout(() => messageDiv.classList.add("hidden"), 5000);
  }

  function updateAuthUI(username = "") {
    signupContainer.hidden = !isTeacher;
    loginButton.classList.toggle("hidden", isTeacher);
    logoutButton.classList.toggle("hidden", !isTeacher);
    authStatus.textContent = isTeacher ? `Signed in as ${username}` : "Not signed in";
    userMenuButton.setAttribute(
      "aria-label",
      isTeacher ? `Teacher account: ${username}` : "Teacher account"
    );
  }

  async function fetchSession() {
    const response = await fetch("/auth/session");
    if (!response.ok) {
      throw new Error("Unable to check teacher login status");
    }
    const session = await response.json();
    isTeacher = session.authenticated;
    updateAuthUI(session.username || "");
  }

  function makeTextElement(tagName, text, className = "") {
    const element = document.createElement(tagName);
    element.textContent = text;
    if (className) {
      element.className = className;
    }
    return element;
  }

  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      if (!response.ok) {
        throw new Error("Unable to load activities");
      }
      const activities = await response.json();
      activitiesList.replaceChildren();
      activitySelect.replaceChildren(new Option("-- Select an activity --", ""));

      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";
        activityCard.appendChild(makeTextElement("h4", name));
        activityCard.appendChild(makeTextElement("p", details.description));
        activityCard.appendChild(
          makeTextElement("p", `Schedule: ${details.schedule}`, "activity-schedule")
        );
        activityCard.appendChild(
          makeTextElement(
            "p",
            `Availability: ${details.max_participants - details.participants.length} spots left`
          )
        );

        const participantsContainer = document.createElement("div");
        participantsContainer.className = "participants-container";
        if (details.participants.length > 0) {
          const participantsSection = document.createElement("div");
          participantsSection.className = "participants-section";
          participantsSection.appendChild(makeTextElement("h5", "Participants:"));
          const participantsList = document.createElement("ul");
          participantsList.className = "participants-list";

          details.participants.forEach((email) => {
            const participant = document.createElement("li");
            participant.appendChild(makeTextElement("span", email, "participant-email"));
            if (isTeacher) {
              const removeButton = makeTextElement("button", "Remove", "delete-btn");
              removeButton.type = "button";
              removeButton.dataset.activity = name;
              removeButton.dataset.email = email;
              removeButton.setAttribute("aria-label", `Remove ${email} from ${name}`);
              removeButton.addEventListener("click", handleUnregister);
              participant.appendChild(removeButton);
            }
            participantsList.appendChild(participant);
          });
          participantsSection.appendChild(participantsList);
          participantsContainer.appendChild(participantsSection);
        } else {
          participantsContainer.appendChild(
            makeTextElement("p", "No participants yet", "no-participants")
          );
        }
        activityCard.appendChild(participantsContainer);
        activitiesList.appendChild(activityCard);

        activitySelect.add(new Option(name, name));
      });
    } catch (error) {
      activitiesList.replaceChildren(
        makeTextElement("p", "Failed to load activities. Please try again later.")
      );
      console.error("Error fetching activities:", error);
    }
  }

  async function handleUnregister(event) {
    const button = event.currentTarget;
    const activity = button.dataset.activity;
    const email = button.dataset.email;
    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(activity)}/unregister?email=${encodeURIComponent(email)}`,
        { method: "DELETE" }
      );
      const result = await response.json();
      if (!response.ok) {
        showMessage(result.detail || "Unable to unregister student", "error");
        if (response.status === 401) {
          isTeacher = false;
          updateAuthUI();
          await fetchActivities();
        }
        return;
      }
      showMessage(result.message, "success");
      await fetchActivities();
    } catch (error) {
      showMessage("Failed to unregister. Please try again.", "error");
      console.error("Error unregistering:", error);
    }
  }

  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const email = document.getElementById("email").value;
    const activity = activitySelect.value;
    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(activity)}/signup?email=${encodeURIComponent(email)}`,
        { method: "POST" }
      );
      const result = await response.json();
      if (!response.ok) {
        showMessage(result.detail || "Unable to register student", "error");
        if (response.status === 401) {
          isTeacher = false;
          updateAuthUI();
          await fetchActivities();
        }
        return;
      }
      showMessage(result.message, "success");
      signupForm.reset();
      await fetchActivities();
    } catch (error) {
      showMessage("Failed to sign up. Please try again.", "error");
      console.error("Error signing up:", error);
    }
  });

  userMenuButton.addEventListener("click", () => {
    const isExpanded = userMenuButton.getAttribute("aria-expanded") === "true";
    userMenuButton.setAttribute("aria-expanded", String(!isExpanded));
    userMenu.classList.toggle("hidden", isExpanded);
  });

  loginButton.addEventListener("click", () => {
    userMenu.classList.add("hidden");
    userMenuButton.setAttribute("aria-expanded", "false");
    loginDialog.showModal();
  });

  document.getElementById("cancel-login").addEventListener("click", () => {
    loginDialog.close();
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(loginForm);
    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: formData.get("username"),
          password: formData.get("password"),
        }),
      });
      const result = await response.json();
      if (!response.ok) {
        showMessage(result.detail || "Unable to sign in", "error");
        return;
      }
      isTeacher = true;
      updateAuthUI(result.username);
      loginForm.reset();
      loginDialog.close();
      showMessage("Teacher signed in", "success");
      await fetchActivities();
    } catch (error) {
      showMessage("Failed to sign in. Please try again.", "error");
      console.error("Error signing in:", error);
    }
  });

  logoutButton.addEventListener("click", async () => {
    try {
      const response = await fetch("/auth/logout", { method: "POST" });
      if (!response.ok) {
        throw new Error("Unable to log out");
      }
      isTeacher = false;
      updateAuthUI();
      userMenu.classList.add("hidden");
      userMenuButton.setAttribute("aria-expanded", "false");
      await fetchActivities();
      showMessage("Teacher signed out", "success");
    } catch (error) {
      showMessage("Failed to sign out. Please try again.", "error");
      console.error("Error signing out:", error);
    }
  });

  async function initialize() {
    try {
      await fetchSession();
    } catch (error) {
      updateAuthUI();
      console.error("Error checking teacher session:", error);
    }
    await fetchActivities();
  }

  initialize();
});
