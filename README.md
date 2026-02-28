# Open GRC

Plateforme open source de Gouvernance, Risques et Conformité (GRC).

## Prérequis

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

## Démarrage rapide

1. Copier le fichier d'environnement :

```bash
cp .env.example .env
```

2. Lancer les services :

```bash
docker compose up --build
```

3. Appliquer les migrations (dans un autre terminal) :

```bash
docker compose exec web python manage.py migrate
```

4. Créer un superutilisateur :

```bash
docker compose exec web python manage.py createsuperuser
```

L'application est accessible sur [http://localhost:8000](http://localhost:8000).
L'interface d'administration est sur [http://localhost:8000/admin/](http://localhost:8000/admin/).

## Stack technique

- Python 3.12
- Django 5.2 LTS
- PostgreSQL 16
- Docker & Docker Compose

## Licence

MIT
