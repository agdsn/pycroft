alias drip="docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'"
export ip=$(drip pycroft_dev-db_1)
export URI="postgres://postgres:password@$ip/pycroft"
psql $URI -c 'create schema if not exists pycroft'
pg_restore -U postgres  -h $(drip pycroft_dev-db_1) -d pycroft pycroft_for_abe_importer.sql --role=postgres -O -c
psql "postgres://postgres:password@$ip/pycroft" \
	-c 'drop trigger if exists duplicate_username_check_trigger on pycroft."user";'
