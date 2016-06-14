from vizone.payload.user_group.aclentry import AclEntry


def set_group_permissions(acl, group_name, read=True, write=True, admin=True):
    """
    Make sure a group is in the ACL and that is has the correct rights, If no
    rights are true, the group entry will be removed.

    Args:
        acl vizone.payload.user_group.aclentry.Acl: The ACL to operate on
        group_name str: The name of the group
        read bool: Read right
        write bool: Write right
        admin bool: Admin right

    Returns:
        bool: True if altered, False otherwise
    """
    if not any((read, write, admin)):
        before = len(acl.groupentries)
        acl.groupentries = [
            groupentry for groupentry in acl.groupentries if groupentry.name != group_name
        ]
        return len(acl.groupentries) < before

    for group in acl.groupentries:
        if group.name == group_name:
            touched = False
            if group.read != read:
                group.read = read
                touched = True
            if group.write != write:
                group.write = write
                touched = True
            if group.admin != admin:
                group.admin = admin
                touched = True
            return touched

    group = AclEntry(name=group_name, read=read, write=write, admin=admin)
    acl.groupentries.append(group)

    return True
