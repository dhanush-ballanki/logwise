ERROR_RULES = [
    {
        'id': 'non_zero_exit',
        'condition': lambda log: log['exit_code'] != 0,
        'description': 'Command failed with non-zero exit code.',
        'root_cause': 'Possible reasons: Invalid arguments, missing dependencies, or runtime errors. Check stderr for details.',
        'fixes': 'Verify command syntax, install missing packages, or debug the script.'
    },
    {
        'id': 'permission_denied',
        'condition': lambda log: 'permission denied' in log['stderr'].lower(),
        'description': 'Permission denied error detected.',
        'root_cause': 'Insufficient permissions.',
        'fixes': 'Run with sudo, change file ownership (chown), or adjust permissions (chmod).'
    },
    {
        'id': 'file_not_found',
        'condition': lambda log: 'no such file or directory' in log['stderr'].lower(),
        'description': 'File or directory not found.',
        'root_cause': 'Path issue.',
        'fixes': 'Check if the file exists (ls), correct the path, or create the missing item.'
    },
    # Add more as needed
]

def apply_rules(log: dict) -> list:
    issues = []
    for rule in ERROR_RULES:
        if rule['condition'](log):
            issues.append({
                'rule_id': rule['id'],
                'description': rule['description'],
                'root_cause': rule['root_cause'],
                'fixes': rule['fixes']
            })
    return issues