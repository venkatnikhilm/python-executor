# Requirements Document

## Introduction

The Secure Code Executor is a web service that accepts arbitrary Python code via HTTP API and executes it in a sandboxed environment using nsjail for security isolation. The service provides execution results including stdout, stderr, return codes, and handles timeouts and resource limits. The system is designed to be deployed on GCP Cloud Run as a containerized Flask application.

## Glossary

- **Secure Code Executor**: The complete web service system that accepts and executes Python code
- **nsjail**: A lightweight process isolation tool that provides security sandboxing
- **Flask Application**: The HTTP web server component that handles API requests
- **Executor Module**: The component responsible for validating input, invoking nsjail, and capturing execution results
- **Sandbox Environment**: An isolated execution context with restricted system access and resource limits
- **Cloud Run**: Google Cloud Platform's serverless container deployment platform

## Requirements

### Requirement 1

**User Story:** As an API client, I want to submit Python code for execution via HTTP POST, so that I can run code remotely without managing infrastructure.

#### Acceptance Criteria

1. WHEN a client sends a POST request to the /execute endpoint with valid JSON containing Python code THEN the Secure Code Executor SHALL accept the request and return a 200 status code
2. WHEN the request body contains a "code" field with Python source code THEN the Secure Code Executor SHALL extract and prepare the code for execution
3. WHEN the request body is missing the "code" field THEN the Secure Code Executor SHALL return a 400 status code with an error message
4. WHEN the request body contains invalid JSON THEN the Secure Code Executor SHALL return a 400 status code with an error message
5. WHEN the code executes successfully THEN the Secure Code Executor SHALL return a JSON response containing stdout, stderr, return_code, and execution status

### Requirement 2

**User Story:** As a system administrator, I want code execution to be isolated in a secure sandbox, so that malicious code cannot compromise the host system or access sensitive resources.

#### Acceptance Criteria

1. WHEN Python code is executed THEN the Executor Module SHALL invoke nsjail with security restrictions configured
2. WHEN code attempts to access the filesystem outside allowed paths THEN the Sandbox Environment SHALL deny access
3. WHEN code attempts network operations THEN the Sandbox Environment SHALL deny access based on nsjail configuration
4. WHEN code attempts to spawn additional processes THEN the Sandbox Environment SHALL enforce process limits
5. WHEN nsjail configuration is loaded THEN the Executor Module SHALL validate that security policies are properly defined

### Requirement 3

**User Story:** As an API client, I want execution results to include stdout, stderr, and return codes, so that I can understand what happened during code execution.

#### Acceptance Criteria

1. WHEN executed code writes to stdout THEN the Secure Code Executor SHALL capture and return the output in the response
2. WHEN executed code writes to stderr THEN the Secure Code Executor SHALL capture and return the error output in the response
3. WHEN code execution completes THEN the Secure Code Executor SHALL return the process exit code
4. WHEN code execution times out THEN the Secure Code Executor SHALL return a timeout indicator and partial output if available
5. WHEN nsjail fails to start THEN the Secure Code Executor SHALL return an error response with diagnostic information

### Requirement 4

**User Story:** As a system administrator, I want execution to have time and resource limits, so that runaway code cannot consume excessive resources.

#### Acceptance Criteria

1. WHEN code execution exceeds the configured timeout THEN the Executor Module SHALL terminate the process
2. WHEN the timeout is reached THEN the Secure Code Executor SHALL return a response indicating timeout occurred
3. WHEN nsjail is invoked THEN the Executor Module SHALL apply memory limits as specified in configuration
4. WHEN nsjail is invoked THEN the Executor Module SHALL apply CPU limits as specified in configuration
5. WHERE resource limits are configured in nsjail.cfg THEN the Executor Module SHALL enforce those limits during execution

### Requirement 5

**User Story:** As a developer, I want the service to be containerized with Docker, so that it can be deployed consistently across environments.

#### Acceptance Criteria

1. WHEN the Docker image is built THEN the Dockerfile SHALL include all required dependencies including Python, Flask, and nsjail
2. WHEN the container starts THEN the Flask Application SHALL listen on the configured port
3. WHEN building the Docker image THEN the build process SHALL exclude unnecessary files using .dockerignore
4. WHEN the container runs THEN the Flask Application SHALL be accessible via HTTP requests
5. WHERE the service is deployed to Cloud Run THEN the container SHALL respond to HTTP requests on the PORT environment variable

### Requirement 6

**User Story:** As a DevOps engineer, I want a deployment script for GCP Cloud Run, so that I can easily deploy the service to production.

#### Acceptance Criteria

1. WHEN the deployment script is executed THEN the script SHALL build the Docker image
2. WHEN the Docker image is built THEN the script SHALL push the image to Google Container Registry
3. WHEN the image is pushed THEN the script SHALL deploy the service to Cloud Run
4. WHEN deploying to Cloud Run THEN the script SHALL configure appropriate memory and CPU allocations
5. WHEN deployment completes THEN the script SHALL output the service URL

### Requirement 7

**User Story:** As an API client, I want clear documentation with cURL examples, so that I can quickly understand how to use the service.

#### Acceptance Criteria

1. WHEN a developer reads the README THEN the documentation SHALL include the project structure
2. WHEN a developer reads the README THEN the documentation SHALL include API endpoint descriptions
3. WHEN a developer reads the README THEN the documentation SHALL include cURL examples for the /execute endpoint
4. WHEN a developer reads the README THEN the documentation SHALL include example request and response payloads
5. WHEN a developer reads the README THEN the documentation SHALL include deployment instructions
