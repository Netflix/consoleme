---
description: ConsoleMe
---

# Architecture

ConsoleMe is a Python Tornado web application backed by Redis, DynamoDB, and \(optionally\) S3. For local development, our [docker-compose-dependencies.yaml file](https://github.com/Netflix/consoleme/blob/master/docker-compose-dependencies.yaml) can be used for local DynamoDB and Redis.  

![Architecture Diagram](.gitbook/assets/consoleme-diagram-1-.png)

## DynamoDB Tables

ConsoleMe makes use of several DynamoDB tables. If you plan to have a multi-region deployment of ConsoleMe, you must make these DynamoDB tables **global** in your production environment. The configuration of these tables is defined [here](https://github.com/Netflix/consoleme/blob/master/scripts/initialize_dynamodb_oss.py). 

| Table Name | Table Contents |
| :--- | :--- |
| consoleme\_iamroles\_global | A cache of your IAM roles.  |
| consoleme\_config\_global | ConsoleMe's [Dynamic Configuration](configuration/dynamic-configuration.md) |
| consoleme\_policy\_requests | User-submitted policy requests |
| consoleme\_resource\_cache | Resources cached from [AWS Config](configuration/resource-syncing.md) |
| consoleme\_cloudtrail | An aggregation of recent cloudtrail errors associated with your resources. \(Note: The OSS code will not generate this for you yet\) |

## Redis

## S3

