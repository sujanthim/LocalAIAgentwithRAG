#!/usr/bin/env python3
"""
CLI tool for managing users in the SQLite credential store.

Usage:
    python manage_users.py add --username alice --role hr --email alice@medcare.com
    python manage_users.py list
    python manage_users.py change-password --username alice
    python manage_users.py delete --username alice
"""

import argparse
import getpass
import sys

from user_store import add_user, delete_user, init_db, list_users, update_password

VALID_ROLES = {"admin", "hr", "billing", "public"}


def cmd_add(args):
    password = getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        sys.exit("Passwords do not match.")
    if not password:
        sys.exit("Password cannot be empty.")
    try:
        add_user(args.username, password, args.role, args.email)
        print(f"User '{args.username}' added (role: {args.role}).")
    except Exception as e:
        sys.exit(f"Error: {e}")


def cmd_list(_args):
    users = list_users()
    if not users:
        print("No users found.")
        return
    print(f"\n{'Username':<20} {'Role':<12} {'Email':<32} Created")
    print("-" * 85)
    for u in users:
        print(f"{u['username']:<20} {u['role']:<12} {u['email']:<32} {u['created_at']}")
    print()


def cmd_change_password(args):
    password = getpass.getpass("New password: ")
    confirm = getpass.getpass("Confirm new password: ")
    if password != confirm:
        sys.exit("Passwords do not match.")
    if not password:
        sys.exit("Password cannot be empty.")
    update_password(args.username, password)
    print(f"Password updated for '{args.username}'.")


def cmd_delete(args):
    confirm = input(f"Delete user '{args.username}'? This cannot be undone. (yes/no): ").strip()
    if confirm.lower() != "yes":
        print("Cancelled.")
        return
    delete_user(args.username)
    print(f"User '{args.username}' deleted.")


def main():
    init_db()

    parser = argparse.ArgumentParser(description="Manage users for LocalAIAgentWithRAG.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="Add a new user")
    p_add.add_argument("--username", required=True)
    p_add.add_argument("--role", required=True, choices=sorted(VALID_ROLES))
    p_add.add_argument("--email", required=True)

    sub.add_parser("list", help="List all users")

    p_cp = sub.add_parser("change-password", help="Change a user's password")
    p_cp.add_argument("--username", required=True)

    p_del = sub.add_parser("delete", help="Delete a user")
    p_del.add_argument("--username", required=True)

    args = parser.parse_args()
    {"add": cmd_add, "list": cmd_list, "change-password": cmd_change_password, "delete": cmd_delete}[
        args.command
    ](args)


if __name__ == "__main__":
    main()
