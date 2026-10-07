# Migrating Instances from Grove

We are going to simplify the migration by making the new instance to use the old instance data. This allows us to avoid data migration, but requires careful configuration of the new instance. Both instances will be using the same database and storage for some time!

## Preparation

1. Set the DNS records of the instance TTL to 300s.
2. In the Grove cluster repository, use `control/tutor.sh config save` to generate the full Tutor config for the instance.
3. This guide covers the steps to migrate an instance using an external database. If the instance uses PVCs on the cluster to store any data (Aspects for example), plan a migration path for it before starting.
4. Get access to the Launchpad cluster's ArgoCD UI. OPTIONALLY, get the `kubeconfig` file to access the cluster for debugging.
5. Get the `kubeconfig` for the Grove cluster.
5. Clone the cluster repository locally.

## Migration

!!! note

    The Launchpad cluster operates fully on Gitops principles via ArgoCD. This guide presents the steps for performing the migration in a dedicated Git branch, allowing full PR review workflow. It is not a hard requirement, all of these steps can be done directly on the `main` branch of the cluster if required.

### Stage 1 - Deploy the target instance

1. Create a new instance using the [Create Instance](../instances/provisioning.md) workflow.
1. Pull the changes to the repo locally, create a new branch.
1. If the Tutor version and the plugin versions don't match the migrating instance, update them.

    !!! tip

        Tutor plugins are installed via `PICASSO_EXTRA_COMMANDS` using `pip install`. *pip*'s dependency resolution could cause unintended versions of dependencies to be installed. Create `tutor-plugins.txt` in the pip requirements.txt format and install all the plugins using a single `pip install -r tutor-plugins.txt` for a cleaner dependency resolution.

1. Copy default values like Django Secret, OAuth Client Secret..etc., of the LMS and CMS from the Grove's `config.yml`.
1. Push the changes to Github and create a PR.
1. Build and deploy the instance with **Build all images** Github Workflow. Use the custom branch name for both **Use workflow from** and **Branch to clone the strain from** fields.
1. Login to ArgoCD, verify that the instance is being deployed. Wait until both "Sync" and "Health" states to be green. (~20 mins for the first deployment)

**:material-flag: Checkpoint:** The instance should be live at `instance-name.<cluster-domain>` domain.

### Stage 2 - Apply customizations

#### 2.1 Plugins

1. Add custom plugins used by the instance to `tutor-plugins.txt`.
1. Create the `instances/<my-instance>/plugins` directory and copy the local plugins used by the instance from Grove cluster's `plugins` directory.
1. Update `config.yml`
    * Add the plugins to `PLUGINS` list
    * Add the plugins to `tutor plugins enable ...` command under `PICASSO_EXTRA_COMMANDS`
1. Copy any plugin specific config from the Grove instances `config.yml`.

!!! warning

    Take special care when copying database related values to avoid overwriting existing data. When it doubt use provided by the plugins or use new values.

#### 2.2 Theming

Follow the [Theming](../instances/theming.md) docs and configure the comprehensive and MFE themes. Make sure to migrate theming config from `grove.yml` of the instance to appropriate values.

#### 2.3 Update the instance

1. Commit, push the changes.
1. Run the **Build all images** workflow again for the instance to be updated.
1. Verify the changes take effect and instances is healthy in ArgoCD.
1. Create a test user and check the customizations are applied correctly.

!!! tip

    ArgoCD's lms, cms, lms-worker, cms-worker pods provide a **Terminal** tab for running management commands. This is extremely useful if kubeconfig is not available for direct cluster access.

**:material-flag:Checkpoint:** Theme and other customizations are applied and the instace mirrors the Grove instance.

### Stage 3 - Point the new instance to the old instance data

#### 3.1 Stop auto-sync

1. Turn off the init jobs for the new instance by setting `DRYDOCK_INIT_JOBS` to `false` in `config.yml`
1. Turn off ArgoCD Auto-Sync by setting `spec.syncPolicy.automated.enabled` to `false` in `application.yml`
1. Redeploy using the "Build all images" workflow.
1. Verify Auto Sync is disabled in the ArgoCD UI.

#### 3.2 Remap Database

1. Get the application configuration from the old instance

    ```shell
    # List all configmaps
    kubectl get cm -n psu-ag-stage --sort-by='{.metadata.creationTimestamp}'

    # LMS configuration
    ./kubectl -n <instance-name> get cm openedx-settings-lms-<latest id> \
      -o jsonpath='{.data.production\.py}' > <instance-name>-settings-lms.py

    ./kubectl -n <instance-name> get cm openedx-config-<latest id> \
      -o jsonpath='{.data.lms\.env\.yml}' > <instance-name>-lms.env.yml

    # CMS configuration
    ./kubectl -n <instance-name> get cm openedx-settings-cms-<latest id> \
      -o jsonpath='{.data.production\.py}' > <instance-name>-settings-cms.py

    # if other configuration is needed, get it from the old instance
    # -- recommended to get from instance settings using Django shell
    # ./kubectl -n <instance-name> exec -it deployments/lms -- ./manage.py lms shell
    ```

1. Update the MySQL, MongoDB, S3 and other configuration in the new instance config to use the old instance data (i.e. the same database and storage)
1. Enable the new cluster access for old databases (MongoDB and MySQL)
1. Update the instance config and images using the **Build all images** GitHub workflow
1. Make a backup of the old instance data (in MySQL, MongoDB, S3, etc.)
1. Deploy the new instance using ArgoCD's *Refresh* and *Sync*. Wait for it to be healthy. **Now both instances are sharing the same database**
1. If Meilisearch of the instance is backed by a PVC, update *Meilisearch indices*. Open a terminal on the CMS pod,

    ```sh
    ./manage.py cms reindex_studio
    ./manage.py cms reindex_course --active
    ```

1. Login using an user account from the old instance. Check instance specific configuration and make sure non-generic configuration is working as expected (e.g., LTI, OAuth, etc.)

**:material-flag: Checkpoint:** LMS and Studio work with an account from the old instance. ArgoCD is in Sync and Healthy.

### Stage 4 - DNS Changes

We need to update the DNS records to point to the new instance. This may lead to a 0-7 minutes outage while the Let's Encrypt certificates are (re-)generated. This section is split into 2 sections: safe and unsafe operations. Proceed in order.

#### Safe operations

1. Change the domain names from `<instance>.cluster.domain` to the actual domain.
1. Prepare the image and configuration by running the **Build all images** workflow.

#### Unsafe operations

1. Change the DNS record to point to the new cluster, and wait about a minute for DNS propagation (monitor DNS at [https://dnschecker.org/]). For CNAME aliased record, the propagation may take a bit longer.
1. From ArgoCD UI, click **Refresh** and then **Sync**.
1. Wait for the sync to finish and the instance to be healthy.
1. Proceed with the instance test checklist on Listaflow to verify the new instance is working as expected
1. check the logs for errors
1. update the DNS record TTL to 3600s once confirmed that the instance is OK
1. Once everything is verified - In the ArgoCD UI, click **Sync** and check **Prune** to clear out all the outdated resources like old configmaps and ingresses.

**:material-flag:Checkpoint:** The instance is live and healthy in the instances original URL.

#### Enable ArgoCD automated sync

Enable ArgoCD automated sync for the new instance by setting `spec.syncPolicy.automated.enabled` to `true` in the `application.yml`

!!! tip

    If the migration was done from a custom branch, this is a good stage to review and merge the PR to the `main` branch.

## Swap Terraform resources

_**IMPORTANT: Do this step if and only if ALL instances are migrated from the cluster!**_

TBD -- This section of the documentation will be finalized when the first cluster is migrated at OpenCraft and we discovered all rabbit holes.

## Ensure instance permissions are correct

The new infrastructure uses proper permissions for the instance resources, but the old infrastructure does not. We need to make sure the instance user has access only to the instance resources and not the entire database cluster(s).

The new infrastructure grants:

- **MySQL**: `ALL PRIVILEGES` on the instance database only (e.g. ```GRANT ALL PRIVILEGES ON `launchpad-instance-openedx`.* TO 'launchpad-instance'@'%'```), not on `*.*`
- **MongoDB**: `readWrite` role on the instance's main and forum databases only, not `readWriteAnyDatabase` or other cluster-wide roles

### Step 1: Identify instance database values

- From the migrated instance `config.yml` or Kubernetes configmaps, note:

- `MYSQL_DATABASE` (e.g. `launchpad-instance-openedx`)
- `MYSQL_USERNAME` (e.g. `launchpad-instance`)
- `MONGODB_DATABASE` (e.g. `launchpad-instance-openedx`)
- `FORUM_MONGODB_DATABASE` (e.g. `launchpad-instance-forum`)
- `MONGODB_USERNAME` (e.g. `launchpad-instance`)

_Note: example values will be used below._

### Step 2: Restrict MySQL permissions

- If the instance user has global privileges (e.g. on `*.*`), restrict it to the instance database only.

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

- Follow the steps for your MongoDB provider:

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

1. In Atlas: Project -> Database Access -> edit the user.

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

- Ensure the instance can connect to MySQL and MongoDB (LMS/CMS healthy)
- Run the instance test checklist in Listaflow to confirm expected behaviour
