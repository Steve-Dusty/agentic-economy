"""
System manifest parsing and deployment service.

Handles YAML parsing, validation, agent naming, and deployment orchestration.
"""
import yaml
import re
import logging
from typing import Dict, List, Tuple, Optional

from models import SystemManifest, SystemAgentConfig, SystemPermissions, SystemViewConfig
from database import db
from db_models import ScheduleCreate, SystemViewCreate

logger = logging.getLogger(__name__)


def parse_manifest(yaml_str: str) -> SystemManifest:
    """
    Parse YAML string into SystemManifest.

    Raises:
        ValueError: If YAML is invalid or missing required fields
    """
    try:
        data = yaml.safe_load(yaml_str)
    except yaml.YAMLError as e:
        raise ValueError(f"YAML parse error: {str(e)}")

    if not data:
        raise ValueError("Empty manifest")

    if not isinstance(data, dict):
        raise ValueError("Manifest must be a YAML object")

    # Validate required fields
    if "name" not in data:
        raise ValueError("Missing required field: name")
    if "agents" not in data or not data["agents"]:
        raise ValueError("Missing required field: agents (must have at least 1)")

    # Parse agents
    agents = {}
    for agent_name, agent_config in data["agents"].items():
        if not isinstance(agent_config, dict):
            raise ValueError(f"Agent '{agent_name}' config must be an object")
        if "template" not in agent_config:
            raise ValueError(f"Agent '{agent_name}' missing required field: template")

        agents[agent_name] = SystemAgentConfig(
            template=agent_config["template"],
            resources=agent_config.get("resources"),
            folders=agent_config.get("folders"),
            schedules=agent_config.get("schedules"),
            tags=agent_config.get("tags")  # ORG-001 Phase 4
        )

    # Parse permissions
    permissions = None
    if "permissions" in data:
        perm_data = data["permissions"]
        permissions = SystemPermissions(
            preset=perm_data.get("preset"),
            explicit=perm_data.get("explicit")
        )

    # ORG-001 Phase 4: Parse default_tags
    default_tags = data.get("default_tags")

    # ORG-001 Phase 4: Parse system_view
    system_view = None
    if "system_view" in data:
        sv_data = data["system_view"]
        if isinstance(sv_data, dict) and "name" in sv_data:
            system_view = SystemViewConfig(
                name=sv_data["name"],
                icon=sv_data.get("icon"),
                color=sv_data.get("color"),
                shared=sv_data.get("shared", True)
            )

    return SystemManifest(
        name=data["name"],
        description=data.get("description"),
        prompt=data.get("prompt"),
        agents=agents,
        permissions=permissions,
        default_tags=default_tags,
        system_view=system_view
    )


def validate_manifest(manifest: SystemManifest) -> List[str]:
    """
    Validate manifest and return warnings.

    Returns:
        List of warning messages (empty if all valid)

    Raises:
        ValueError: If validation fails
    """
    warnings = []

    # Validate system name
    if not re.match(r'^[a-z0-9][a-z0-9-]{0,48}[a-z0-9]$|^[a-z0-9]{1,2}$', manifest.name):
        raise ValueError(
            f"Invalid system name '{manifest.name}': must be 1-50 chars, "
            "lowercase alphanumeric and hyphens, start/end with alphanumeric"
        )

    # Validate agent names
    for agent_name in manifest.agents.keys():
        if not re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$', agent_name):
            raise ValueError(
                f"Invalid agent name '{agent_name}': must be lowercase alphanumeric and hyphens"
            )

    # Validate template references
    for agent_name, config in manifest.agents.items():
        template = config.template
        if not (template.startswith("github:") or template.startswith("local:")):
            raise ValueError(
                f"Agent '{agent_name}': template must start with 'github:' or 'local:'"
            )

    # Validate permissions
    if manifest.permissions:
        if manifest.permissions.preset and manifest.permissions.explicit:
            raise ValueError("Cannot specify both preset and explicit permissions")

        if manifest.permissions.preset:
            valid_presets = ["full-mesh", "orchestrator-workers", "none"]
            if manifest.permissions.preset not in valid_presets:
                raise ValueError(
                    f"Invalid permission preset '{manifest.permissions.preset}': "
                    f"must be one of {valid_presets}"
                )

            # Warn if orchestrator-workers but no orchestrator agent
            if manifest.permissions.preset == "orchestrator-workers":
                if "orchestrator" not in manifest.agents:
                    warnings.append(
                        "Permission preset 'orchestrator-workers' specified but no "
                        "'orchestrator' agent defined. No permissions will be granted."
                    )

        if manifest.permissions.explicit:
            agent_names = set(manifest.agents.keys())
            for source, targets in manifest.permissions.explicit.items():
                if source not in agent_names:
                    raise ValueError(f"Unknown agent in permissions: {source}")
                for target in targets:
                    if target not in agent_names:
                        raise ValueError(f"Unknown agent in permissions: {target}")

    # Validate schedules (if any)
    for agent_name, config in manifest.agents.items():
        if config.schedules:
            for i, schedule in enumerate(config.schedules):
                if "name" not in schedule:
                    raise ValueError(f"Agent '{agent_name}' schedule {i}: missing 'name'")
                if "cron" not in schedule:
                    raise ValueError(f"Agent '{agent_name}' schedule {i}: missing 'cron'")
                if "message" not in schedule:
                    raise ValueError(f"Agent '{agent_name}' schedule {i}: missing 'message'")

    # ORG-001 Phase 4: Validate tags
    tag_pattern = re.compile(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$')

    # Validate default_tags
    if manifest.default_tags:
        for tag in manifest.default_tags:
            if not tag_pattern.match(tag.lower().strip()):
                raise ValueError(
                    f"Invalid tag '{tag}': must be lowercase alphanumeric and hyphens"
                )

    # Validate per-agent tags
    for agent_name, config in manifest.agents.items():
        if config.tags:
            for tag in config.tags:
                if not tag_pattern.match(tag.lower().strip()):
                    raise ValueError(
                        f"Agent '{agent_name}' has invalid tag '{tag}': "
                        "must be lowercase alphanumeric and hyphens"
                    )

    # Validate system_view name
    if manifest.system_view:
        if not manifest.system_view.name or not manifest.system_view.name.strip():
            raise ValueError("system_view.name is required")

    return warnings


def agent_exists(name: str) -> bool:
    """Check if an agent with this name already exists."""
    # Check database for ownership record
    owner = db.get_agent_owner(name)
    return owner is not None


def get_next_agent_name(base_name: str) -> str:
    """
    Find next available name with _N suffix if base name exists.

    Examples:
        "my-agent" -> "my-agent" (if doesn't exist)
        "my-agent" -> "my-agent_2" (if my-agent exists)
        "my-agent" -> "my-agent_3" (if my-agent and my-agent_2 exist)
    """
    if not agent_exists(base_name):
        return base_name

    n = 2
    while agent_exists(f"{base_name}_{n}"):
        n += 1
    return f"{base_name}_{n}"


def resolve_agent_names(
    system_name: str,
    agents: Dict[str, SystemAgentConfig]
) -> Tuple[Dict[str, str], List[str]]:
    """
    Resolve short agent names to final names, handling conflicts.

    Args:
        system_name: The system name prefix
        agents: Dict of short_name -> agent config

    Returns:
        Tuple of (name_mapping, warnings)
        - name_mapping: {short_name: final_name}
        - warnings: List of conflict warnings
    """
    name_mapping = {}
    warnings = []

    for short_name in agents.keys():
        base_name = f"{system_name}-{short_name}"
        final_name = get_next_agent_name(base_name)
        name_mapping[short_name] = final_name

        if final_name != base_name:
            warnings.append(
                f"Agent '{base_name}' already exists, will create '{final_name}'"
            )

    return name_mapping, warnings


# ============================================================================
# Phase 2: Configuration Functions
# ============================================================================

async def configure_permissions(
    agent_names: Dict[str, str],  # {short_name: final_name}
    permissions: Optional[SystemPermissions],
    created_by: str
) -> int:
    """
    Apply permission configuration based on preset or explicit rules.

    Args:
        agent_names: Mapping of short names to final agent names
        permissions: Permission configuration from manifest
        created_by: Username for audit trail

    Returns:
        Number of permissions configured
    """
    if not permissions:
        return 0

    final_names = list(agent_names.values())
    permissions_count = 0

    if permissions.preset == "full-mesh":
        # Every agent can communicate with every other agent
        for source in final_names:
            targets = [t for t in final_names if t != source]
            if targets:
                db.set_agent_permissions(source, targets, created_by)
                permissions_count += len(targets)
                logger.info(f"Granted {source} permissions to call: {targets}")

    elif permissions.preset == "orchestrator-workers":
        # Only orchestrator can call workers
        # Workers cannot call anyone (clear their default permissions)
        orchestrator_short = "orchestrator"
        if orchestrator_short in agent_names:
            orchestrator = agent_names[orchestrator_short]
            workers = [n for n in final_names if n != orchestrator]
            if workers:
                # Set orchestrator permissions to call all workers
                db.set_agent_permissions(orchestrator, workers, created_by)
                permissions_count = len(workers)
                logger.info(f"Granted {orchestrator} permissions to call workers: {workers}")

                # Clear worker permissions (set to empty list = clear all)
                for worker in workers:
                    db.set_agent_permissions(worker, [], created_by)
                    logger.info(f"Cleared permissions for worker {worker}")

    elif permissions.preset == "none":
        # No permissions - clear all default permissions for all system agents
        for agent in final_names:
            db.set_agent_permissions(agent, [], created_by)
        logger.info(f"Cleared all permissions for {len(final_names)} agents (preset: none)")

    elif permissions.explicit:
        # Apply explicit permission matrix
        # First, clear permissions for all system agents not in explicit config
        for short_name, final_name in agent_names.items():
            if short_name not in permissions.explicit:
                db.set_agent_permissions(final_name, [], created_by)
                logger.info(f"Cleared default permissions for {final_name} (not in explicit config)")

        # Then set explicit permissions
        for source_short, target_shorts in permissions.explicit.items():
            source = agent_names.get(source_short)
            if not source:
                logger.warning(f"Unknown source agent in permissions: {source_short}")
                continue
            targets = [agent_names[t] for t in target_shorts if t in agent_names]
            # set_agent_permissions does a full replacement
            db.set_agent_permissions(source, targets, created_by)
            permissions_count += len(targets)
            if targets:
                logger.info(f"Granted {source} permissions to call: {targets}")
            else:
                logger.info(f"Cleared permissions for {source} (empty target list)")

    return permissions_count


def configure_folders(
    agent_names: Dict[str, str],  # {short_name: final_name}
    agents_config: Dict[str, SystemAgentConfig]
) -> int:
    """
    Configure shared folder settings for all agents.

    Args:
        agent_names: Mapping of short names to final agent names
        agents_config: Agent configurations from manifest

    Returns:
        Number of folder configs created
    """
    folders_configured = 0

    for short_name, config in agents_config.items():
        final_name = agent_names.get(short_name)
        if not final_name:
            continue

        if config.folders:
            expose = config.folders.get("expose", False)
            consume = config.folders.get("consume", False)

            db.upsert_shared_folder_config(
                agent_name=final_name,
                expose_enabled=expose,
                consume_enabled=consume
            )
            folders_configured += 1
            logger.info(f"Configured folders for {final_name}: expose={expose}, consume={consume}")

    return folders_configured


def create_schedules(
    agent_names: Dict[str, str],  # {short_name: final_name}
    agents_config: Dict[str, SystemAgentConfig],
    owner_username: str
) -> int:
    """
    Create schedules for all agents.

    Args:
        agent_names: Mapping of short names to final agent names
        agents_config: Agent configurations from manifest
        owner_username: Username for schedule ownership

    Returns:
        Number of schedules created
    """
    schedules_count = 0

    for short_name, config in agents_config.items():
        final_name = agent_names.get(short_name)
        if not final_name or not config.schedules:
            continue

        for schedule_data in config.schedules:
            schedule_create = ScheduleCreate(
                name=schedule_data["name"],
                cron_expression=schedule_data["cron"],
                message=schedule_data["message"],
                enabled=schedule_data.get("enabled", True),
                timezone=schedule_data.get("timezone", "UTC"),
                description=schedule_data.get("description")
            )

            # Create schedule in database
            schedule = db.create_schedule(
                agent_name=final_name,
                username=owner_username,
                schedule_data=schedule_create
            )

            if schedule:
                schedules_count += 1
                logger.info(f"Created schedule '{schedule_data['name']}' for {final_name}")
                # Dedicated scheduler syncs from database automatically
            else:
                logger.warning(f"Failed to create schedule '{schedule_data['name']}' for {final_name}")

    return schedules_count


# ============================================================================
# ORG-001 Phase 4: Tags and System View Functions
# ============================================================================

def configure_tags(
    system_name: str,
    agent_names: Dict[str, str],  # {short_name: final_name}
    agents_config: Dict[str, SystemAgentConfig],
    default_tags: Optional[List[str]] = None
) -> int:
    """
    Configure tags for all agents.

    - system_prefix is automatically added as a tag to all agents
    - default_tags (from manifest) are added to all agents
    - per-agent tags (from agent config) are added to specific agents

    Args:
        system_name: The system name prefix (auto-applied as tag)
        agent_names: Mapping of short names to final agent names
        agents_config: Agent configurations from manifest
        default_tags: Default tags to apply to all agents

    Returns:
        Total number of tags configured
    """
    tags_count = 0

    for short_name, config in agents_config.items():
        final_name = agent_names.get(short_name)
        if not final_name:
            continue

        # Build combined tag list
        combined_tags = []

        # 1. Auto-apply system_prefix as tag (always first)
        combined_tags.append(system_name)

        # 2. Add default_tags (from manifest root)
        if default_tags:
            combined_tags.extend(default_tags)

        # 3. Add per-agent tags
        if config.tags:
            combined_tags.extend(config.tags)

        # Normalize and dedupe tags
        normalized_tags = list(set(t.lower().strip() for t in combined_tags if t.strip()))

        if normalized_tags:
            db.set_agent_tags(final_name, normalized_tags)
            tags_count += len(normalized_tags)
            logger.info(f"Configured {len(normalized_tags)} tags for {final_name}: {normalized_tags}")

    return tags_count


def create_system_view(
    system_name: str,
    system_view: SystemViewConfig,
    default_tags: Optional[List[str]],
    owner_id: str
) -> Optional[str]:
    """
    Create a System View for the deployed system.

    The view filters by:
    - system_prefix tag (always included)
    - default_tags (if specified)

    Args:
        system_name: The system name prefix
        system_view: System view configuration from manifest
        default_tags: Default tags to include in filter
        owner_id: User ID for view ownership

    Returns:
        View ID if created, None if failed
    """
    try:
        # Build filter tags
        filter_tags = [system_name]  # Always include system prefix
        if default_tags:
            filter_tags.extend(default_tags)

        # Normalize and dedupe
        filter_tags = list(set(t.lower().strip() for t in filter_tags if t.strip()))

        # Create the view
        view_data = SystemViewCreate(
            name=system_view.name,
            description=f"Auto-created for {system_name} system deployment",
            icon=system_view.icon,
            color=system_view.color,
            filter_tags=filter_tags,
            is_shared=system_view.shared
        )

        view = db.create_system_view(owner_id, view_data)
        if view:
            logger.info(f"Created System View '{system_view.name}' with filter tags: {filter_tags}")
            return view.id
        else:
            logger.warning(f"Failed to create System View '{system_view.name}'")
            return None

    except Exception as e:
        logger.error(f"Error creating System View: {e}")
        return None


async def start_all_agents(agent_names: List[str]) -> Dict[str, str]:
    """
    Start all created agents.

    This triggers Trinity meta-prompt injection with the updated trinity_prompt.

    Args:
        agent_names: List of agent names to start

    Returns:
        Dict of {agent_name: status} where status is 'started' or error message
    """
    from routers.agents import start_agent_internal

    results = {}
    for agent_name in agent_names:
        try:
            result = await start_agent_internal(agent_name)
            results[agent_name] = "started"
            logger.info(f"Started agent '{agent_name}': {result}")
        except Exception as e:
            results[agent_name] = f"error: {str(e)}"
            logger.warning(f"Failed to start agent '{agent_name}': {e}")
            # Continue starting other agents even if one fails

    return results


def export_manifest(system_name: str, agents: List[Dict]) -> str:
    """
    Export a system as a YAML manifest.

    Args:
        system_name: The system prefix
        agents: List of agent dictionaries from Docker

    Returns:
        YAML string representing the system configuration
    """
    # Extract short names (remove system prefix)
    agent_configs = {}
    for agent in agents:
        full_name = agent['name']
        # Remove system prefix and hyphen
        short_name = full_name[len(system_name) + 1:]

        # Get agent details
        config = {
            "template": agent.get('template', 'local:business-assistant')
        }

        # Get resources (if available from labels)
        if agent.get('resources'):
            config["resources"] = agent['resources']

        # Get folders config from database
        try:
            folder_config = db.get_agent_folder_config(full_name)
            if folder_config and (folder_config['expose_enabled'] or folder_config['consume_enabled']):
                config["folders"] = {
                    "expose": bool(folder_config['expose_enabled']),
                    "consume": bool(folder_config['consume_enabled'])
                }
        except Exception as e:
            logger.warning(f"Failed to get folder config for {full_name}: {e}")

        # Get schedules from database
        try:
            schedules = db.list_agent_schedules(full_name)
            if schedules:
                config["schedules"] = [
                    {
                        "name": s.name,
                        "cron": s.cron_expression,
                        "message": s.message,
                        "enabled": bool(s.enabled),
                        "timezone": s.timezone
                    }
                    for s in schedules
                ]
        except Exception as e:
            logger.warning(f"Failed to get schedules for {full_name}: {e}")

        # ORG-001 Phase 4: Get tags from database
        try:
            agent_tags = db.get_agent_tags(full_name)
            # Filter out the system prefix tag (auto-applied on import)
            # so export shows only explicitly configured tags
            non_prefix_tags = [t for t in agent_tags if t != system_name]
            if non_prefix_tags:
                config["tags"] = non_prefix_tags
        except Exception as e:
            logger.warning(f"Failed to get tags for {full_name}: {e}")

        agent_configs[short_name] = config

    # Build manifest dict
    manifest_dict = {
        "name": system_name,
        "description": f"Exported system configuration for {system_name}",
        "agents": agent_configs
    }

    # Get permissions (try to detect preset pattern)
    try:
        # Check first agent's permissions to infer pattern
        if agents:
            first_agent = agents[0]['name']
            perms = db.get_agent_permissions(first_agent)

            if perms:
                # Try to detect full-mesh pattern
                all_agents_names = [a['name'] for a in agents]
                permitted_targets = [p["target_agent"] for p in perms]

                # Full-mesh: agent can call all other agents
                expected_targets = [n for n in all_agents_names if n != first_agent]
                if set(permitted_targets) == set(expected_targets):
                    # Verify other agents also have full-mesh
                    is_full_mesh = True
                    for agent in agents:
                        agent_perms = db.get_agent_permissions(agent['name'])
                        expected = [n for n in all_agents_names if n != agent['name']]
                        actual = [p["target_agent"] for p in agent_perms]
                        if set(actual) != set(expected):
                            is_full_mesh = False
                            break

                    if is_full_mesh:
                        manifest_dict["permissions"] = {"preset": "full-mesh"}
                    else:
                        # Export explicit permissions
                        explicit_perms = {}
                        for agent in agents:
                            short_name = agent['name'][len(system_name) + 1:]
                            agent_perms = db.get_agent_permissions(agent['name'])
                            targets = [
                                p["target_agent"][len(system_name) + 1:]
                                for p in agent_perms
                            ]
                            if targets:
                                explicit_perms[short_name] = targets

                        if explicit_perms:
                            manifest_dict["permissions"] = {"explicit": explicit_perms}
                else:
                    # Export explicit permissions
                    explicit_perms = {}
                    for agent in agents:
                        short_name = agent['name'][len(system_name) + 1:]
                        agent_perms = db.get_agent_permissions(agent['name'])
                        targets = [
                            p["target_agent"][len(system_name) + 1:]
                            for p in agent_perms
                            if p["target_agent"].startswith(f"{system_name}-")
                        ]
                        if targets:
                            explicit_perms[short_name] = targets

                    if explicit_perms:
                        manifest_dict["permissions"] = {"explicit": explicit_perms}

    except Exception as e:
        logger.warning(f"Failed to export permissions for system {system_name}: {e}")

    # Get global trinity_prompt if it exists
    try:
        trinity_prompt = db.get_setting_value("trinity_prompt")
        if trinity_prompt:
            manifest_dict["prompt"] = trinity_prompt
    except Exception as e:
        logger.warning(f"Failed to get trinity_prompt: {e}")

    # Convert to YAML
    yaml_output = yaml.dump(manifest_dict, default_flow_style=False, sort_keys=False, allow_unicode=True)

    return yaml_output
