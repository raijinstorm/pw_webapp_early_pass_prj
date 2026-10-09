# ConfigHub

Governed configuration management for a Databricks-based analytics platform.

The company, clients and people described here are fictional.

### The company

**Northstack Analytics** sells analytics products to mid-size and large companies in retail, consumer goods and
pharma. Each product is a recurring data delivery that runs for a client:

| Product | What the client gets |
|---|---|
| **Pricing Feed** | Daily price files for the client's shop systems, with promotions and discount limits applied |
| **Sales Forecast** | A weekly demand forecast per store and article, used for purchasing and staffing |
| **Inventory Sync** | Stock levels synchronised between the client's warehouses and Northstack's central tables |
| … | about 20 more: assortment analysis, churn models, promotion effectiveness, … |

Everything runs on **Databricks**: ingestion **pipelines**, scheduled **jobs**, **machine learning** models
and, more recently, AI-assisted analysis. Northstack started with a handful of clients and two products. Today it
serves **hundreds of clients** with **more than 20 products**, and **over 100 people** (data engineers, analysts,
client-success managers) work on the platform.

### How configuration is managed today

The pipelines are shared, but **no two clients are the same**. Every product needs per-client settings: where the
source data lives, which currency to use, how often to refresh, discount limits, which forecasting model,
the forecast horizon, the warehouse code, who to notify when a run fails, and so on.

These settings live in **more than a thousand Excel and CSV files on Azure Blob Storage**, which the Databricks
jobs read at run time:



Changing one value means: find the right file, download it, edit it locally, upload it back and hope it was
the latest copy. The result:

- **Mistakes reach production.** A typo in a path or a currency code is only discovered when the nightly job
  fails, and the client's delivery is late.
- **No governance.** Anyone with storage access can change any client's settings. Nobody owns a file.
- **No history.** When something breaks, nobody can tell who changed what, when, or why, or how to roll back.
- **Stale copies.** Files get copied, renamed and re-uploaded; several versions of "the" config exist.
- **It's slow.** A one-value change takes minutes of download/edit/upload, and often a message to an engineer.

### Why Databricks alone doesn't solve it

Databricks is excellent at processing data, but it has **no UI for people to edit data by hand**.

Moving the configuration from files into Delta tables would make it governed and versioned, but it wouldn't make it
editable: there's no screen where a client-success manager opens a table, changes one client's refresh interval
and saves. The only way to change a row is to write SQL (`UPDATE … WHERE client = …`) in a notebook or the SQL
editor. That's too much friction for the 100+ people who maintain configurations, many of whom don't write SQL, and
nothing checks the new value against business rules ("between 1 and 168 hours", "one of EUR/USD/PLN") before it's
used by the next run.

So people fall back to what they can edit by hand, which is spreadsheets, and the problems above follow.
Northstack's data team decided to build a small internal tool for exactly this job: **a UI on top of the
configuration**, with validation, per-product permissions and history built in.

### The solution: ConfigHub

ConfigHub sits between the people and the platform. Jobs and pipelines still read their configuration, but people
change it through an app with validation, permissions and history, instead of by uploading files.



| Problem today | How ConfigHub solves it |
|---|---|
| Typos reach production | Each product has a **schema** (types, ranges, options, patterns). Invalid values are rejected when they're saved, with a clear message, not discovered in a failed nightly run. |
| No governance | **Role-based access per product.** Only members see a product's configurations; only managers change its schema and members. |
| No history | **Every save is a new immutable version** with author, time and comment. Versions can be compared and restored. |
| Stale copies | **One current version** per product and client, in one place. |
| Slow changes | Find, edit, save: one form, seconds, no engineer needed. |

### Roles and use cases

| Role | Scope | Can |
|---|---|---|
| **Admin** | whole system | everything; manages users, products, clients and memberships in the admin panel |
| **Manager** | per product | everything an editor can, plus manage the product's schema and members, disable/activate configurations, restore old versions |
| **Editor** | per product | view and edit the configurations of their products |

Main use cases:

1. **Change a value.** An editor raises a client's refresh interval; the value is validated against the schema and saved as version N+1.
2. **Evolve a product.** A manager adds a schema field (e.g. `currency`, one of EUR/USD/PLN), and it appears in every edit form for that product.
3. **Roll back a bad change.** A manager sees a suspicious change in the history, compares it with the previous version and restores the old values.
4. **Manage access.** A manager adds a colleague to the product as an editor, or removes them.
5. **Find things.** Anyone filters configurations (product, client, status, search) and the change history (product, author, date range).
6. **Recover an account.** A user who forgot their password resets it through an email link.

## First technical choices

Python 3.12, Django, PostgreSQL and server-rendered Bootstrap pages. Start with Django models and normal HTML forms. Docker Compose will run the app and database.

`confighub/` contains settings, `app/` the application, `static/` styling and `docs/` supporting material.
