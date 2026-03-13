# Migrating Instances from Grove

## Configure the new instance

-[ ] set the DNS record TTL to 300s
-[ ] create a new instance in the new cluster using the "create instance" GitHub workflow
-[ ] make sure the new instance's `aplication.yml` has `spec.syncPolicy.automated.enabled` set to `false`
-[ ] create any necessary infrastructure resources for the new instance (used by plugins)
-[ ] ensure the old instance configuration (`config.yml`) is replicated for the new instance
-[ ] configure theming and branding for the new instance
-[ ] build the new instance using the "build instance" GitHub workflow
-[ ] deploy the new instance using ArgoCD and wait for it to be ready (~20 minutes for the first deployment)
-[ ] check that the new instance looks as expected
-[ ] proceed with instance test guide to verify the instance is working as expected
-[ ] turn off the init jobs for the new instance by setting `DRYDOCK_INIT_JOBS` to `false` in the `config.yml`

## Point the new instance to the old instance data

We are going to simplify the migration by making the new instance to use the old instance data. This allows us to avoid data migration, but requires careful configuration of the new instance. Both instances will be using the same database and storage for some time!

-[ ] get the application configuration from the old instance

   ```shell
   # List all configmaps
   ./kubectl -n <instance-name> get cm

   # LMS configuration
   ./kubectl -n <instance-name> get cm openedx-settings-lms-<latest id> \
     -o jsonpath='{.data.production\.py}' > <instance-name>-settings-lms.py

   # CMS configuration
   ./kubectl -n <instance-name> get cm openedx-settings-cms-<latest id> \
     -o jsonpath='{.data.production\.py}' > <instance-name>-settings-cms.py

   # if other configuration is needed, get it from the old instance
   # -- recommended to get from instance settings using Django shell
   # ./kubectl -n <instance-name> exec -it deployments/lms -- ./manage.py lms shell
   ```

-[ ] update the MySQL, MongoDB, S3 and other configuration in the new instance config to use the old instance data (i.e. the same database and storage)
-[ ] enable the new cluster access for old databases (MongoDB and MySQL)
-[ ] build the new instance using the "build instance" GitHub workflow
-[ ] make a backup of the old instance data (in MySQL, MongoDB, S3, etc.)
-[ ] deploy the new instance using ArgoCD and wait for it to be ready
-[ ] proceed with instance test guide to verify the old instance is still working as expected
-[ ] check instance specific configuration and make sure non-generic configuration is working as expected (e.g., LTI, OAuth, etc.)

## DNS changes

We need to update the DNS records to point to the new instance. This may lead to a 0-7 minutes outage while the Let's Encrypt certificates are (re-)generated. This section is split into 2 sections: safe and unsafe operations. Proceed in order.

Safe operations:

-[ ] update the instance config with the expected FQDNs for LMS, CMS, etc.
-[ ] build the new instance using the "build instance" GitHub workflow

Unsafe operations:

-[ ] change the DNS record to point to the new cluster, and wait about a minute for DNS propagation (monitor DNS at [https://dnschecker.org/]). For CNAME aliased record, the propagation may take a bit longer.
-[ ] (optional -- only if a must) destroy ingress controllers [^1] and TLS secrets [^2]
-[ ] (optional -- only if a must) deploy the new instance using ArgoCD and wait for it to be ready
-[ ] proceed with instance test guide to verify the new instance is working as expected
-[ ] check the logs for errors
-[ ] update the DNS record TTL to 3600s once confirmed that the instance is OK

[^1]: `kubectl -n courses delete ing --all`
[^2]: `kubectl -n courses delete secrets cms-host-tls lms-host-tls meilisearch-host-tls mfe-host-tls`

## Enable ArgoCD automated sync

-[ ] enable ArgoCD automated sync for the new instance by setting `spec.syncPolicy.automated.enabled` to `true` in the `application.yml`

## Swap Terraform resources

_**IMPORTANT: Do this step if and only if ALL instances are migrated from the cluster!**_

TBD -- This section of the documentation will be finalized when the first cluster is migrated at OpenCraft and we discovered all rabbit holes.

## Ensure instance permissions are correct

The new infrastructure uses proper permissions for the instance resources, but the old infrastructure does not. We need to make sure the instance user has access only to the instance resources and not the entire database cluster(s).

The new infrastructure grants:

- **MySQL**: `ALL PRIVILEGES` on the instance database only (e.g. `GRANT ALL PRIVILEGES ON \`launchpad-instance-openedx\`.* TO 'launchpad-instance'@'%'`), not on `*.*`
- **MongoDB**: `readWrite` role on the instance’s main and forum databases only, not `readWriteAnyDatabase` or other cluster-wide roles

### Step 1: Identify instance database values

-[ ] From the migrated instance `config.yml` or Kubernetes configmaps, note:

- `MYSQL_DATABASE` (e.g. `launchpad-instance-openedx`)
- `MYSQL_USERNAME` (e.g. `launchpad-instance`)
- `MONGODB_DATABASE` (e.g. `launchpad-instance-openedx`)
- `FORUM_MONGODB_DATABASE` (e.g. `launchpad-instance-forum`)
- `MONGODB_USERNAME` (e.g. `launchpad-instance`)

_Note: example values will be used below._

### Step 2: Restrict MySQL permissions

-[ ] If the instance user has global privileges (e.g. on `*.*`), restrict it to the instance database only.

**Prerequisites**: MySQL admin credentials (root or user with `GRANT`) -- allow your IP as a trusted source as needed depending on the Cloud Provider.

1. Connect as admin:

   ```bash
   mysql -h <MYSQL_HOST> -P <MYSQL_PORT> -u <ADMIN_USER> -p
   ```

2. Inspect current grants:

   ```sql
   -- List all users matching the instance username to find the correct host
   SELECT user, host FROM mysql.user WHERE user = 'launchpad-instance';
   SHOW GRANTS FOR 'launchpad-instance'@'%';
   ```

   Use the actual `user@host` from `mysql.user` if it differs from `'%'`. If you see `GRANT ALL PRIVILEGES ON *.*`, the user has cluster-wide access and should be restricted.

3. Revoke global privileges and grant scoped access (replace placeholders; use the actual `user@host` if it differs from `'%'`):

   ```sql
   -- Revoke global privileges (adjust if the user has different grants)
   REVOKE ALL PRIVILEGES ON *.* FROM 'launchpad-instance'@'%';

   -- Grant access only to the instance database
   GRANT ALL PRIVILEGES ON `launchpad-instance-openedx`.* TO 'launchpad-instance'@'%';

   FLUSH PRIVILEGES;
   ```

4. Confirm the grants:

   ```sql
   SHOW GRANTS FOR 'launchpad-instance'@'%';
   ```

   Expected: `GRANT ALL PRIVILEGES ON \`launchpad-instance-openedx\`.* TO 'launchpad-instance'@'%'`.

### Step 3: Restrict MongoDB permissions

-[ ] Follow the steps for your MongoDB provider:

#### DigitalOcean Managed MongoDB (API)

Use the DigitalOcean API to ensure the user has `readWrite` only on the instance databases.

1. Get the cluster ID from your DigitalOcean project or infrastructure config.

2. Check the current user (replace `CLUSTER_ID` and `USERNAME`):

   ```bash
   curl -s -X GET \
     -H "Authorization: Bearer $DIGITALOCEAN_TOKEN" \
     "https://api.digitalocean.com/v2/databases/CLUSTER_ID/users/USERNAME"
   ```

3. If the user has cluster-wide access, recreate it with scoped databases:

   ```bash
   # Delete the existing user (note: this invalidates the password; you must update the instance config with the new one)
   curl -s -X DELETE \
     -H "Authorization: Bearer $DIGITALOCEAN_TOKEN" \
     "https://api.digitalocean.com/v2/databases/CLUSTER_ID/users/USERNAME"

   # Wait a few seconds, then create the user with scoped access
   sleep 3
   curl -s -X POST \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $DIGITALOCEAN_TOKEN" \
     -d '{"name": "USERNAME", "settings": {"mongo_user_settings": {"databases": ["launchpad-instance-openedx", "launchpad-instance-forum"], "role": "readWrite"}}}' \
     "https://api.digitalocean.com/v2/databases/CLUSTER_ID/users"
   ```

   Update the instance `config.yml` with the new MongoDB password from the API response.

#### MongoDB Atlas

Use the Atlas UI or CLI to give the user `readWrite` only on the instance databases.

1. In Atlas: Project → Database Access → edit the user.

2. Ensure the user has roles:

   - `readWrite` on the main database (e.g. `launchpad-instance-openedx`)
   - `readWrite` on the forum database (e.g. `launchpad-instance-forum`)

3. Remove any cluster-wide roles such as `readWriteAnyDatabase` or `readAnyDatabase`.

Or via Atlas CLI:

```bash
atlas dbusers update launchpad-instance \
  --role "readWrite@launchpad-instance-openedx" \
  --role "readWrite@launchpad-instance-forum" \
  --projectId <PROJECT_ID>
```

#### Self-hosted MongoDB (mongo shell)

Use `mongosh` (MongoDB 5.0+). On older setups, use `mongo` if `mongosh` is not available.

1. Connect as admin:

   ```bash
   mongosh "mongodb://<ADMIN_USER>:<ADMIN_PASSWORD>@<MONGODB_HOST>:<MONGODB_PORT>/admin?authSource=admin"
   ```

2. Inspect current roles:

   ```javascript
   use admin
   db.getUser("launchpad-instance")
   ```

3. Replace roles with scoped `readWrite` (adjust usernames and database names):

   ```javascript
   use admin
   db.updateUser("launchpad-instance", {
     roles: [
       { role: "readWrite", db: "launchpad-instance-openedx" },
       { role: "readWrite", db: "launchpad-instance-forum" }
     ]
   })
   ```

   If the user does not exist, create it instead:

   ```javascript
   use admin
   db.createUser({
     user: "launchpad-instance",
     pwd: "<PASSWORD_FROM_CONFIG>",
     roles: [
       { role: "readWrite", db: "launchpad-instance-openedx" },
       { role: "readWrite", db: "launchpad-instance-forum" }
     ]
   })
   ```

### Step 4: Verify the instance works

-[ ] Ensure the instance can connect to MySQL and MongoDB (LMS/CMS healthy)
-[ ] Run the instance test guide to confirm expected behaviour
