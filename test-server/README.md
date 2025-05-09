# Local test/dev server
To enable the local test server, copy the override dockerfile one dir
up, additionally, add the test server in the config.toml. To do this,
this command may be useful:

```bash
cat ./test-server/test-server-config.toml >> ./config.toml \
&& cp ./test-server/docker-compose.override.yaml ./
```


