
# Contributing to JTS

Thank you for considering contributing to JTS! We're excited to collaborate with you. This document outlines the process for contributing, so please read it carefully before you start.

## How Can I Contribute?

### 1. Reporting Bugs
If you've found a bug, please create an issue in our [GitHub Issues](https://github.com/pprasquier/JTS/issues) section. When reporting a bug, please include:

- **A clear and descriptive title**
- **A detailed description of the problem**
- **Steps to reproduce the issue**
- **Expected and actual behavior**
- **Any relevant screenshots or code snippets**

### 2. Suggesting Enhancements
We welcome ideas for new features! To suggest an enhancement:

- Open a new issue in our [GitHub Issues](https://github.com/pprasquier/JTS/issues) section.
- Provide a clear and descriptive title.
- Explain why this enhancement would be useful.
- Describe the proposed solution.

### 3. Submitting a Pull Request
If you're ready to start coding, follow these steps:

1. **Fork the repository** and clone it to your local machine.
2. **Create a new branch** for your work:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** with clear, descriptive commit messages.
4. If your code requires/provides new settings options, add those settings to the existing 0_0....json file or in a new .json file with a name starting with 0_. This way, they will be included in the git sync. Be sure to leave all exsiting default settings as they are. If you need to override them locally, just create new json settings files with a name that doesn't start with 0_.   
5. **Run tests** to ensure your changes work as expected.
6. **Push your branch** to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
7. **Open a Pull Request** in the main repository:
   - Provide a clear description of what you did and why.
   - Reference any related issues or discussions.
   - Ensure that all tests pass on the CI/CD pipeline.

### 4. Coding Guidelines
- **Code Style:** Follow the coding style used in the project. This may include specific formatting rules, naming conventions, or indentation practices.
- **Tests:** Include tests for any new functionality. Ensure existing tests pass after your changes.
- **Documentation:** Update any relevant documentation, including comments in the code, README, or dedicated documentation files.


## Getting Help
If you need any help or have questions, feel free to reach out by opening an issue, or check our [Discussion Board](https://github.com/pprasquier/JTS/issues) if available.

## Thank You!
We appreciate your time and effort in contributing to JTS. Together, we can make this project even better!
