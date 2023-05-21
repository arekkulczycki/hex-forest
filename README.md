### Migrations ###

At the very start, just once, run:
`aerich init-db`

For the following migrations

To create a migration, run:
`aerich migrate --name <MIGRATION NAME>`

To apply changes on the database, run:
`aerich upgrade`

To rollback: `aerich downgrade -v`
