# Theming

Theming an Open edX instance involves 2 parts:

- **Legacy UI:**  Using comprehensive theming. This is natively [supported by Tutor](https://docs.tutor.edly.io/tutorials/theming.html).
- **MFEs:** Using Design Tokens. This is supported by the [grove-simple-theme](https://gitlab.com/opencraft/dev/tutor-contrib-grove/-/tree/main/tutorgrove/plugins/simple_theme) Tutor plugin using [edx-simple-theme](https://github.com/open-craft/edx-simple-theme).

## Customizing an Instance

### Legacy UI using a comprehensive theme

Tutor requires the comprehensive theme to be added to an instance' `env` directory in a specific path. That can be accomplished using `PICASSO_EXTRA_COMMANDS` in the instance's `config.yml`. For example:

```yaml
PICASSO_EXTRA_COMMANDS:
  # Clone the comprehensive theme to the build directory as Tutor expects
  - git clone https://github.com/my-org/my-theme.git "$(tutor config printroot)/env/build/openedx/themes/my-theme"
```

This will add `my-theme` to the `openedx` Docker image and can activated by changing the *Site theme* for LMS or Studio from the Django Admin.

!!! warning "Important"

    The `edx-simple-theme` from OpenCraft historically supported customizing both the legacy LMS UI elements and the MFEs in a single package. This is **no longer the case**. If an instance uses it for customizing the legacy UI parts:

    1. If the instance is using a release branch like `release/teak`, create a branch from it. If the instance already has a custom branch, go to next step.
    2. Remove the following from `.gitignore`
       * `lms/static/sass/_lms-overrides.scss`
       * `lms/static/sass/common-variables.scss`
    3. Create those 2 files. Could be empty, or add your customizations.
    4. Commit and push your branch
    5. Use the new branch in the `git clone` command under `PICASSO_EXTRA_COMMANDS`.

    This is required as, historically, these files were created by Grove from instance configuration.

### MFEs using Design Tokens

Theming using Design Tokens is the only theming system from the Ulmo release and beyond. It involves defining the branding customizations in design token spec and then using Paragon CLI to compile it to CSS, which can then be included in the MFEs.

The *edx-simple-theme* with the *grove-simple-theme* Tutor plugin simplify this process for instance operators.

1. Declare the cutomization values under `GROVE_THEMES` in `config.yml`.
1. Install *tutor-contrib-grove*, enable *grove-simple-theme* plugin and generate the theme tokens using `PICASSO_EXTRA_COMMANDS`.

```yaml
GROVE_THEMES:
  core:
    size.border.radius.base: 0
    size.border.radius.lg: 0
    size.border.radius.sm: 0
PICASSO_EXTRA_COMMADS:
  - pip install git+https://gitlab.com/opencraft/dev/tutor-contrib-grove
  - tutor plugins enable grove-simple-theme
  - tutor generate-tokens
```

!!! tip

    The `grove-simple-theme` plugin supports plain CSS to be added using `SIMPLE_THEME_EXTRA_CSS` attribute in `config.yml` as well.

## Related Documentation

- [Theming configuration](https://gitlab.com/opencraft/dev/tutor-contrib-grove/) section for more details on theming using `GROVE_THEMES`
- [edx-simple-theme](https://github.com/open-craft/edx-simple-theme) - The skeleton used to customize the themes of Open edX instances.
