The following are a few notes for setting up a production-ready configuration for StockBot. They assume that the user is running StockBot on a unix-like machine.

## Opening firewall ports

The simplest way to open ports on your host is likely to use firewalld.

To install firewalld:
* CentOS/RHEL: `sudo yum install firewalld`
* Ubuntu: `sudo apt-get install firewalld`

Then you can open ports as follows:
```
# Ports 80/443
sudo firewall-cmd --permanent --zone=public --add-service=http
sudo firewall-cmd --permanent --zone=public --add-service=https
sudo firewall-cmd --reload

# Other ports
sudo firewall-cmd --permanent --zone=public --add-port=8000/tcp
sudo firewall-cmd --reload
```

If firewalld is unavailable to you, you can also use iptables. Here are some sample rules:
```
# Open HTTP/S ports
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT
```

## Configuring web server

Although Django's default web server is fine for testing/debugging purposes, it's not meant for production, and doesn't natively support features such as SSL.

If you want to have a more production-ready server, one of the simplest architecture setups is nginx -> uWSGI -> django. nginx is a web server, and uwsgi converts the requests from that web server into a language that django can understand.

### uWSGI:

To install:
```
pip install uwsgi
```

You will need a `uwsgi_params` file to run uwsgi. A file with sensible defaults is present in this project at [uwsgi_params](../uwsgi_params).

You can then start your application using uwsgi instead of Django's runserver. To start on port 8000, from the StockBot project directory:
```
uwsgi --module StockBot.wsgi --socket :8000
```

You can also use a Unix socket instead, assuming you intend to set up a web server which points to it:
```
uwsgi --module StockBot.wsgi --socket StockBot.sock
```

#### uWSGI configuration file

Instead of having to specify uWSGI options on the command line for every run, you can set these options in a .ini file. A sample file with sensible defaults is present at [uwsgi.ini](../uwsgi.ini). It is configured to run StockBot on port 8000 by default. Feel free to view the settings in this file and modify them as desired.

You can then run StockBot with these configurations as follows:
```
uwsgi --ini uwsgi.ini
```

If daemonizing StockBot, to stop the server (using the safe-pidfile option configured in the default [uwsgi.ini](../uwsgi.ini)):
```
kill -INT `cat /tmp/StockBot.pid`
```
...or to reload the server...

```
kill -HUP `cat /tmp/StockBot.pid`
```

### nginx
To install nginx:

* CentOS/RHEL: `sudo yum install nginx`
* Ubuntu: `sudo apt-get install nginx`

On CentOS/RHEL, you should enable nginx as a service:
```
sudo systemctl enable nginx
```

You can then start/stop nginx as follows:
* CentOS/RHEL: `sudo systemctl [start/stop/restart] nginx`
* Ubuntu: `/etc/init.d/nginx [start/stop/restart]`

#### Basic nginx configuration

The default configuration file will be located at `/etc/nginx/nginx.conf`. You *could* modify this file directly, though the following pattern is generally more advisable:

1. Define a `nginx.conf` file in the root of your StockBot project directory. A file with sensible defaults is already present at [nginx.conf](../nginx.conf). Feel free to tweak it as necessary.
```
# the upstream component nginx needs to connect to
upstream django {
    # server unix:///path/to/StockBot/StockBot.sock; # for a file socket
    server 127.0.0.1:8000; # for a web port socket (we'll use this first)
}

# configuration of the server
server {
    # the port your site will be served on
    listen      80;
    # the domain name it will serve for
    server_name mystockbot.com; # substitute your machine's IP address or FQDN
    charset     utf-8;

    # max upload size
    client_max_body_size 75M;   # adjust to taste

    # Finally, send all non-media requests to the Django server.
    location / {
        uwsgi_pass  django;
        include     /path/to/StockBot/uwsgi_params; # the uwsgi_params file you installed
    }
}
```
2. Create a directory `/etc/nginx/sites-enabled` and create a symlink to your StockBot nginx.conf file in the directory:
```
sudo mkdir /etc/nginx/sites-enabled
sudo ln -s /path/to/StockBot/nginx.conf /etc/nginx/sites-enabled/
```
3. Add the following line to the bottom of the `http` section in the `/etc/nginx/nginx.conf` file:
```
include /etc/nginx/sites-enabled/*.conf;
```
4. Start StockBot with uwsgi:
```
uwsgi --module StockBot.wsgi --socket :8000
```
or to use a Unix socket:
```
uwsgi --module StockBot.wsgi --socket StockBot.sock
```
or to use the options defined in a .ini file:
```
uwsgi --ini uwsgi.ini
```

4. Restart nginx:
CentOS/RHEL7:
```
sudo systemctl restart nginx
```
Ubuntu:
```
/etc/init.d/nginx restart
```
5. Ensure that the bot is reachable. Try hitting the following endpoint from a browser:
`http://mystockbot.com/quotes/view/AAPL`

If you're getting errors, check your nginx error log at `/var/log/nginx/error.log`.

##### Note about Unix sockets

If you're running with a Unix socket and seeing "Permission Denied" errors, nginx likely doesn't have permission to access your socket. You may have to set your socket to a location that is readable to nginx. You may also have to set permissions explicitly on your socket when running it. For example:
```
uwsgi --module StockBot.wsgi --socket StockBot.sock --chmod-socket=664
```

#### Setting up SSL
If you have an SSL certificate and private key, you can configure SSL for StockBot with nginx by modifying your StockBot nginx.conf file as follows:

```
# Main server configuration block for your site
server {
    listen      443 ssl;
    # the domain name it will serve for
    server_name mystockbot.com; # substitute your machine's IP address or FQDN
    ssl_certificate /path/to/certchain.pem;
    ssl_certificate_key /path/to/privkey.pem;
    charset     utf-8;

    # Remaining original options here...
}

# Redirect HTTP requests to HTTPS
server {
    listen 80;
    server_name mystockbot.com;
    return 301 https://mystockbot.com$request_uri;
}
```

## Configuring a database

Portfolios are stored within a database. In order to use the Portfolios feature, you must configure a database for the bot. See [Databases in Django](https://docs.djangoproject.com/en/2.2/ref/databases/) for guidance on configuring a database. You would configure these database settings in the StockBot [database_settings.py](database_settings.py) file.

### Sample Database Configuration - PostgreSQL

If you have the PostgreSQL server installed on your machine, you can quickly set up a database as described below.

#### Creating the database

```
createdb stockbot -O $USER
```

This may fail if your user does not have permissions to modify PostgreSQL databases on your server. You may have to create the `postgres` user and run the command as that user to set up the initial database.

```
sudo adduser postgres
sudo -u postgres createdb stockbot -O $USER
```

This will create a database named "stockbot" which will be owned by the current running user. You should be able to interact this database in the future by running `psql stockbot`.

#### Configuring Django

You will need to specify a database driver for Django to interact with the database. The most commonly used one for PostgreSQL databases is `psycopg2`.

You can install the `pscopg2-binary` for Python as follows:

```
pip install psycopg2-binary
```

You can then configure the settings for this database in the Stockbot [database_settings.py](../StockBot/database_settings.py) file by uncommenting the following section:

```
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'stockbot'
    }
}
```


Finally, run the following to execute the database migrations (you should only need to do this once):

```
python3 manage.py migrate
```
