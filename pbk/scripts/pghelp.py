#!/usr/bin/env python3
import argparse
import subprocess


def parse_arguments():
    parser = argparse.ArgumentParser(description="Create Postgres User & Database")
    parser.add_argument('--username')
    parser.add_argument('--hostname', default="localhost")
    parser.add_argument('--command')

    # Run the parser
    arguments = parser.parse_args()

    # Return the dictionary representation
    return vars(arguments)


def exec_psql_cmd(cmd, db_admin_user="postgres", db_admin_pass="postgres", hostname="localhost", database=None, **kwargs):
    command = ["psql", "-U", db_admin_user, "-w", "-h", hostname, "-c", cmd]
    if database:
        command.extend(['-d', database])
    output = subprocess.run(command, env={"PGPASSWORD": db_admin_pass}, capture_output=True)
    return output


def main():
    args = parse_arguments()
    if cmd := args.get('command'):
        # Run the single command and send the output, useful for debugging
        output = exec_psql_cmd(cmd, **args)
        print(output)

    elif username := args.get('username'):
        create_db_output = exec_psql_cmd(f"create database {username}", **args)
        create_user_output = exec_psql_cmd(f"create user {username} with encrypted password '{username}'", **args)
        grant_all_output = exec_psql_cmd(f"grant all privileges on database {username} to {username}", **args)
        grant_public_schema_output = exec_psql_cmd(f"grant all privileges on schema public to {username}",
                                                   database=username, **args)

        print(create_db_output)
        print(create_user_output)
        print(grant_all_output)
        print(grant_public_schema_output)

    else:
        print(f'Did not get a good set of inputs? \n{args}')




if __name__ == '__main__':
    main()
