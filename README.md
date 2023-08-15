### Migrations ###

At the very start, just once, run:
`aerich init-db`

For the following migrations

To create a migration, run:
`aerich migrate --name <MIGRATION NAME>`

To apply changes on the database, run:
`aerich upgrade`

To rollback: `aerich downgrade -v`


### Run the server ###

In production setup
`PYTHONPATH=. python hex_forest/run.py`

or locally, choosing a target (--help for more info)
`PYTHONPATH=. python hex_forest/run.py -t=local`
