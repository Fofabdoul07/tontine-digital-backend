# 🤝 TONTINE DIGITAL — Guide de déploiement

## ✅ ÉTAPE 1 : Créer un compte GitHub (5 minutes)

1. Allez sur https://github.com
2. Cliquez **"Sign up"** (S'inscrire)
3. Entrez : email, mot de passe, nom d'utilisateur
4. Confirmez votre email
5. ✅ Votre compte GitHub est prêt !

---

## ✅ ÉTAPE 2 : Mettre le code sur GitHub (5 minutes)

1. Connectez-vous sur https://github.com
2. Cliquez le bouton vert **"New"** (ou **"+"** en haut à droite → New repository)
3. Nommez le dépôt : `tontine-digital-backend`
4. Laissez tout le reste par défaut
5. Cliquez **"Create repository"**
6. Sur la page suivante, cliquez **"uploading an existing file"**
7. Glissez-déposez TOUS les fichiers de ce dossier
8. Cliquez **"Commit changes"**
9. ✅ Votre code est sur GitHub !

---

## ✅ ÉTAPE 3 : Déployer sur Render.com (10 minutes)

1. Allez sur https://render.com
2. Cliquez **"Get Started for Free"**
3. Choisissez **"Sign in with GitHub"** (connectez avec votre compte GitHub)
4. Cliquez **"New +"** → **"Web Service"**
5. Sélectionnez votre dépôt `tontine-digital-backend`
6. Configurez ainsi :
   - **Name** : `tontine-digital-api`
   - **Runtime** : `Python`
   - **Build Command** : `pip install -r requirements.txt`
   - **Start Command** : `gunicorn app:app`
   - **Plan** : `Free`
7. Ajoutez les variables d'environnement (section "Environment") :
   - `SECRET_KEY` = `tontine-secret-2026`
   - `JWT_SECRET_KEY` = `tontine-jwt-2026`
   - `ADMIN_WAVE_NUMBER` = `0747429889`
   - `ADMIN_ORANGE_NUMBER` = `0555471974`
   - `ADMIN_MTN_NUMBER` = `0747429889`
   - `SERVICE_FEE_PERCENTAGE` = `0.02`
8. Ajoutez une base de données : **"New +"** → **"PostgreSQL"** → Free
   - Copiez l'URL de connexion dans `DATABASE_URL`
9. Cliquez **"Create Web Service"**
10. Attendez 2-3 minutes que le déploiement se termine
11. ✅ Votre API est publique sur `https://tontine-digital-api.onrender.com`

---

## ✅ ÉTAPE 4 : Tester votre API en ligne

Ouvrez votre navigateur et allez sur :
```
https://tontine-digital-api.onrender.com/health
```

Vous devriez voir :
```json
{
  "status": "OK ✅",
  "app": "Tontine Digital API",
  "version": "1.0.0",
  "admin_accounts": {
    "wave": "0747429889",
    "orange": "0555471974",
    "mtn": "0747429889"
  }
}
```

---

## 📋 LISTE DES ENDPOINTS API

| Méthode | URL | Description |
|---------|-----|-------------|
| GET | /health | Vérifier que l'API fonctionne |
| POST | /api/auth/signup | Créer un compte |
| POST | /api/auth/login | Se connecter |
| GET | /api/auth/me | Mon profil |
| GET | /api/tontines | Mes tontines |
| POST | /api/tontines | Créer une tontine |
| GET | /api/tontines/{id} | Détails d'une tontine |
| POST | /api/tontines/{id}/join | Rejoindre une tontine |
| POST | /api/payments/initiate | Payer une cotisation |
| GET | /api/payments/history | Historique paiements |
| GET | /api/admin/stats | Stats admin |
| GET | /api/admin/users | Liste utilisateurs |
| GET | /api/admin/transactions | Toutes les transactions |

---

## 🧪 TEST RAPIDE (Inscription)

Une fois déployé, testez avec ce lien :
```
POST https://tontine-digital-api.onrender.com/api/auth/signup

Body JSON :
{
  "name": "Mamadou Diallo",
  "phone": "0621234567",
  "password": "monmotdepasse"
}
```

Utilisez l'application **Postman** (gratuite) pour tester facilement.

---

## 📞 Comptes administrateur configurés

- **Wave** : 0747429889
- **Orange Money** : 0555471974  
- **MTN MoMo** : 0747429889

Tous les paiements sont automatiquement dirigés vers ces comptes.
