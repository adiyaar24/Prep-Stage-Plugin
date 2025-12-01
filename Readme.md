# Harness Custom Drone Plugin

A robust drone plugin for Harness CI/CD pipelines with comprehensive error handling and user-friendly configuration management.

## Features

- **🔧 Flexible Configuration**: Support for CLI arguments and environment variables
- **🛡️ Robust Error Handling**: Comprehensive error handling with retry mechanisms and validation
- **📤 Smart Output Management**: Automatic environment variable outputs for seamless pipeline integration
- **🔄 Essential Actions**: Support for create, update, and delete actions
- **🐛 Debug Support**: Detailed logging and debug modes for troubleshooting
- **⚙️ User-Friendly**: Simple parameter passing without cumbersome JSON manipulation

## Quick Start

### CREATE Action Example

```bash
export PLUGIN_ACTION="create"
export PLUGIN_EXECUTION_ID="abc-123-def"
export PLUGIN_TRIGGERED_BY_EMAIL="user@example.com"
export PLUGIN_RESOURCE_CONFIG='{"entries":[{"type":"s3","resource_name":"my-bucket","region":"us-east-1"}]}'
export PLUGIN_USER_DEFINED_NAME="My Test Deployment"
export PLUGIN_DEBUG_MODE="true"

python main.py
```

### UPDATE Action Example

```bash
export PLUGIN_ACTION="update"
export PLUGIN_PRIMARY_OWNER="user@example.com"
export PLUGIN_DEPLOYMENT_NAME="deployment_abc_123_def"
export PLUGIN_RESOURCE_CONFIG='{"entries":[{"type":"s3","resource_name":"my-bucket","versioning":true}]}'
export PLUGIN_COMPONENT_NAME="s3-my-bucket-deployment_abc_123_def"
export PLUGIN_DEBUG_MODE="true"

python main.py
```

### DELETE Action Example

```bash
export PLUGIN_ACTION="delete"
export PLUGIN_PRIMARY_OWNER="user@example.com"
export PLUGIN_DEPLOYMENT_NAME="deployment_abc_123_def"
export PLUGIN_RESOURCE_CONFIG='{"entries":[{"type":"s3","resource_name":"my-bucket"}]}'
export PLUGIN_COMPONENT_NAME="s3-my-bucket-deployment_abc_123_def"
export PLUGIN_DEBUG_MODE="true"

python main.py
```

### Harness Pipeline Integration

```yaml
# In your Harness pipeline
steps:
  - step:
      type: Plugin
      name: Custom Drone Plugin
      identifier: custom_plugin
      spec:
        connectorRef: docker_connector
        image: your-registry/custom-drone-plugin:latest
        settings:
          PLUGIN_ACTION: <+pipeline.variables.action>
          PLUGIN_EXECUTION_ID: <+pipeline.executionId>
          PLUGIN_TRIGGERED_BY_EMAIL: <+pipeline.triggeredBy.email>
          PLUGIN_RESOURCE_CONFIG: <+pipeline.variables.resourceConfig>
```

## Environment Variables Configuration

#### Required Variables

| Variable | CREATE | UPDATE | DELETE | Description | Example |
|----------|--------|--------|--------|--------------|---------|
| `PLUGIN_ACTION` | ✅ | ✅ | ✅ | Action to perform | `"create"`, `"update"`, `"delete"` |
| `PLUGIN_RESOURCE_CONFIG` | ✅ | ✅ | ✅ | Resource configuration (JSON) | `'{"entries":[{"type":"s3","resource_name":"bucket"}]}'` |

#### Action-Specific Required Variables

| Variable | CREATE | UPDATE | DELETE | Description | Example |
|----------|--------|--------|--------|--------------|---------|
| `PLUGIN_EXECUTION_ID` | ✅ | ❌ | ❌ | Pipeline execution ID | `"abc-123-def"` |
| `PLUGIN_TRIGGERED_BY_EMAIL` | ✅ | ❌ | ❌ | Email of triggering user | `"user@example.com"` |
| `PLUGIN_PRIMARY_OWNER` | ❌ | ✅ | ✅ | Primary resource owner | `"user@example.com"` |
| `PLUGIN_DEPLOYMENT_NAME` | ❌ | ✅ | ✅ | Existing deployment name | `"deployment_abc_123_def"` |

#### Optional Variables

| Variable | CREATE | UPDATE | DELETE | Description | Default | Example |
|----------|--------|--------|--------|--------------|---------|---------|
| `PLUGIN_USER_DEFINED_NAME` | ✅ | ❌ | ❌ | Custom deployment name | `""` | `"My Test Deployment"` |
| `PLUGIN_COMPONENT_NAME` | ❌ | ✅ | ✅ | Specific components to target | `""` | `"s3-bucket-deployment_123"` |
| `PLUGIN_LOG_LEVEL` | ✅ | ✅ | ✅ | Logging level | `"info"` | `"debug"`, `"info"`, `"warning"`, `"error"` |
| `PLUGIN_DEBUG_MODE` | ✅ | ✅ | ✅ | Enable debug mode | `false` | `"true"`, `"false"` |
| `PLUGIN_DRY_RUN` | ✅ | ✅ | ✅ | Perform dry run | `false` | `"true"`, `"false"` |
| `PLUGIN_TIMEOUT` | ✅ | ✅ | ✅ | Operation timeout (seconds) | `300` | `"600"` |
| `PLUGIN_RETRY_ATTEMPTS` | ✅ | ✅ | ✅ | Number of retry attempts | `3` | `"5"` |


## Supported Actions

The plugin supports three main actions: **create**, **update**, and **delete**.

### Create Action

Creates new resources and deployments.

**Required Parameters:**
- `execution_id`: Pipeline execution ID
- `triggered_by_email`: User who triggered the pipeline
- `resource_config`: Resource configuration with entries

**Optional Parameters:**
- `user_defined_name`: Custom deployment name
- `advanced_resource_config`: Advanced configuration options

**Output Variables:**
- `RESOURCE_OWNER`: Generated resource owner
- `DEPLOYMENT_NAME`: Generated deployment name
- `USER_DEFINED_DEPLOYMENT_NAME`: Processed user-defined name
- `item_map`: JSON array of workspace mappings
- `workspace_ids`: Comma-separated workspace IDs

**Example:**
```bash
python main.py --action create \
  --execution-id "pipeline-123" \
  --triggered-by-email "developer@company.com" \
  --user-defined-name "My Test Deployment" \
  --resource-config '{
    "entries": [
      {
        "type": "s3",
        "resource_name": "data-bucket",
        "region": "us-west-2"
      },
      {
        "type": "rds",
        "resource_name": "user-db",
        "engine": "postgres"
      }
    ]
  }'
```

### Update Action

Updates existing resources.

**Required Parameters:**
- `primary_owner`: Resource owner
- `deployment_name`: Existing deployment name
- `resource_config`: Resource configuration

**Optional Parameters:**
- `component_name`: Specific components to target

**Output Variables:**
- `RESOURCE_OWNER`: Resource owner
- `RESOURCE_CONFIG`: Processed resource configuration
- `DEPLOYMENT_NAME`: Processed deployment name
- `workspace_ids`: Target workspace IDs

### Delete Action

Deletes existing resources (uses same parameters and outputs as update action).

**Required Parameters:**
- `primary_owner`: Resource owner
- `deployment_name`: Existing deployment name
- `resource_config`: Resource configuration

**Optional Parameters:**
- `component_name`: Specific components to target

**Example:**
```bash
python main.py --action update \
  --primary-owner "developer@company.com" \
  --deployment-name "deployment_pipeline_123" \
  --component-name "s3-data-bucket-deployment_pipeline_123" \
  --resource-config '{
    "entries": [
      {
        "type": "s3",
        "resource_name": "data-bucket",
        "versioning": true
      }
    ]
  }'
```

## Resource Configuration Format

The resource configuration uses a simple JSON structure:

```json
{
  "entries": [
    {
      "type": "resource_type",
      "resource_name": "unique_name",
      "property1": "value1",
      "property2": "value2"
    }
  ]
}
```

### Example Resource Types

```json
{
  "entries": [
    {
      "type": "s3",
      "resource_name": "my-data-bucket",
      "region": "us-east-1",
      "versioning": true
    },
    {
      "type": "rds",
      "resource_name": "user-database",
      "engine": "postgres",
      "instance_class": "db.t3.micro"
    },
    {
      "type": "ec2",
      "resource_name": "web-server",
      "instance_type": "t3.small",
      "ami": "ami-12345678"
    }
  ]
}
```

## Output Management

The plugin automatically sets all outputs as **environment variables** for use in subsequent pipeline steps. No additional configuration required!

### Available Output Variables

**CREATE Action Outputs:**
- `RESOURCE_OWNER` - Generated resource owner
- `DEPLOYMENT_NAME` - Generated deployment name  
- `USER_DEFINED_DEPLOYMENT_NAME` - Processed user-defined name
- `item_map` - JSON array of workspace mappings
- `workspace_ids` - Comma-separated workspace IDs

**UPDATE/DELETE Action Outputs:**
- `RESOURCE_OWNER` - Resource owner
- `RESOURCE_CONFIG` - Processed resource configuration
- `DEPLOYMENT_NAME` - Processed deployment name
- `workspace_ids` - Target workspace IDs

### Output Format

```
RESOURCE_OWNER=user:account/developer@company.com
DEPLOYMENT_NAME=deployment_pipeline_123
workspace_ids=s3-data-bucket-deployment_pipeline_123,rds-user-db-deployment_pipeline_123
item_map=[{"s3-data-bucket-deployment_pipeline_123":{"type":"s3","resource_name":"data-bucket"}}]
```

## Error Handling

The plugin includes comprehensive error handling:

### Validation Errors
- Missing required parameters
- Invalid action types
- Malformed JSON configurations

### Configuration Errors
- Invalid configuration files
- Conflicting parameters
- Missing configuration sources

### Runtime Errors
- File I/O errors
- Network timeouts
- Processing failures

### Retry Mechanism

Failed operations are automatically retried with configurable retry attempts:

```bash
python main.py --action create --retry-attempts 5 --timeout 600
```

## Debug and Troubleshooting

### Enable Debug Mode

```bash
python main.py --debug --action create --execution-id test
```

### Dry Run Mode

```bash
python main.py --dry-run --action create --execution-id test
```

### Verbose Logging

```bash
python main.py --log-level debug --action create
```

### Common Issues

1. **JSON Parsing Errors**: Ensure JSON strings are properly escaped
2. **Missing Parameters**: Check required parameters for your action type
3. **File Permissions**: Ensure output files are writable
4. **Environment Variables**: Verify environment variable names and values

## Integration Examples

### Docker Integration

```dockerfile
FROM python:3.12-slim

# Set metadata
LABEL maintainer="Harness Custom Plugin"
LABEL description="Harness Custom Drone Plugin for CI/CD pipeline automation"
LABEL version="1.0.0"

# Set working directory
WORKDIR /app

# Copy application code
COPY main.py .

# Set environment variables for better Python behavior
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Use exec form for better signal handling
ENTRYPOINT ["python", "main.py"]
```

**Building and Running:**

```bash
# Build the image
docker build -t harness-custom-plugin:latest .

# Run with environment variables
docker run --rm \
  -e PLUGIN_ACTION="create" \
  -e PLUGIN_EXECUTION_ID="test-123" \
  -e PLUGIN_TRIGGERED_BY_EMAIL="user@example.com" \
  -e PLUGIN_RESOURCE_CONFIG='{"entries":[{"type":"s3","resource_name":"test-bucket"}]}' \
  harness-custom-plugin:latest
```

### Harness Pipeline Step

```yaml
- step:
    type: Plugin
    name: Custom Drone Plugin
    identifier: custom_plugin
    spec:
      connectorRef: <+input>
      image: your-registry/harness-plugin:latest
      settings:
        PLUGIN_ACTION: <+pipeline.variables.action>
        PLUGIN_EXECUTION_ID: <+pipeline.executionId>
        PLUGIN_TRIGGERED_BY_EMAIL: <+pipeline.triggeredBy.email>
        PLUGIN_RESOURCE_CONFIG: <+pipeline.variables.resourceConfig>
        PLUGIN_DEBUG_MODE: "false"
```

## Development

### Adding New Actions

1. Add new action to `ActionType` enum
2. Create new processor class inheriting from `ActionProcessor`
3. Implement `validate_inputs()` and `process()` methods
4. Update initialization logic in `DronePlugin.initialize_components()`

### Extending Configuration

1. Add new fields to `PluginConfig` dataclass
2. Update `ConfigLoader._load_from_env()` for environment variable mapping
3. Add CLI arguments to `create_argument_parser()`

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Update documentation
6. Submit a pull request

## Support

For issues and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Enable debug mode for detailed logging
