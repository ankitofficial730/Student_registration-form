document.addEventListener("DOMContentLoaded", () => {
    const form = document.querySelector("form");
    const password = document.querySelector("#password");
    const confirmPassword = document.querySelector("#confirm_password");
    const submitButton = form?.querySelector(
        'button[type="submit"], input[type="submit"]'
    );

    // Password match validation
    function checkPasswordMatch() {
        if (!password || !confirmPassword) return;

        if (
            confirmPassword.value !== "" &&
            password.value !== confirmPassword.value
        ) {
            confirmPassword.setCustomValidity(
                "Passwords do not match."
            );
        } else {
            confirmPassword.setCustomValidity("");
        }
    }

    password?.addEventListener("input", checkPasswordMatch);
    confirmPassword?.addEventListener("input", checkPasswordMatch);

    // Password show/hide buttons
    document.querySelectorAll("[data-toggle-password]").forEach(button => {
        button.addEventListener("click", () => {
            const targetId = button.dataset.togglePassword;
            const input = document.getElementById(targetId);

            if (!input) return;

            const isPassword = input.type === "password";
            input.type = isPassword ? "text" : "password";
            button.textContent = isPassword ? "Hide" : "Show";
            button.setAttribute(
                "aria-label",
                isPassword ? "Hide password" : "Show password"
            );
        });
    });

    // Form validation and loading effect
    form?.addEventListener("submit", event => {
        checkPasswordMatch();

        if (!form.checkValidity()) {
            event.preventDefault();
            form.reportValidity();
            return;
        }

        if (submitButton) {
            submitButton.disabled = true;

            if (submitButton.tagName === "BUTTON") {
                submitButton.textContent = "Please wait...";
            } else {
                submitButton.value = "Please wait...";
            }
        }
    });

    // Automatically remove alerts after 5 seconds
    document.querySelectorAll(".alert").forEach(alert => {
        setTimeout(() => {
            alert.remove();
        }, 5000);
    });
});