# 📚 Guide Claude Code - Gestion du Contexte Mon_PS

Ce dossier contient tous les fichiers nécessaires pour ne plus jamais perdre de contexte avec Claude Code.

---

## 🚀 Installation rapide

### Sur ton serveur Hetzner :

```bash
# 1. Copie ce dossier sur ton serveur
scp -r mon_ps_context/* user@ton-serveur:/home/Mon_ps/

# 2. Ou via Git si tu veux versionner
cd /home/Mon_ps
# Copie les fichiers manuellement
```

### Structure à créer :

```
/home/Mon_ps/
├── CLAUDE.md                    # ← Instructions générales (LU AUTOMATIQUEMENT)
├── docs/
│   ├── CURRENT_TASK.md          # ← Tâche en cours
│   ├── DECISIONS.md             # ← Décisions architecturales
│   └── CHANGELOG.md             # ← Historique des modifications
└── .claude/
    └── commands/
        ├── continue.md          # ← Commande /continue
        ├── save.md              # ← Commande /save
        └── status.md            # ← Commande /status
```

---

## 🎮 Commandes personnalisées

| Commande | Description | Quand l'utiliser |
|----------|-------------|------------------|
| `/continue` | Reprend le contexte complet | Début de chaque session |
| `/save` | Sauvegarde la progression | Avant /compact ou fin de session |
| `/status` | Affiche l'état rapide | Pour voir où on en est |

---

## 📋 Workflow quotidien

### Début de session
```bash
cd /home/Mon_ps
claude

# Dans Claude Code :
/continue
```

### Pendant le travail
- Surveille "Context left: XX%" en bas de l'écran
- À **70%** → utilise `/save` puis `/compact`
- Ou `/save` puis `/clear` si tu changes de tâche

### Fin de session
```bash
# Dans Claude Code :
/save

# Vérifie que tout est sauvegardé, puis :
exit
```

---

## ⚠️ Règles importantes

### NE JAMAIS :
- ❌ Attendre "Context left: 0%" pour agir
- ❌ Utiliser `/clear` sans `/save` avant
- ❌ Oublier de mettre à jour CURRENT_TASK.md

### TOUJOURS :
- ✅ Commencer par `/continue`
- ✅ Sauvegarder avec `/save` avant compact
- ✅ Mettre à jour la progression en fin de session

---

## 🔧 Personnalisation

### Modifier CLAUDE.md
Adapte les sections selon ton projet :
- Ajoute tes commandes bash fréquentes
- Mets à jour la structure du projet
- Ajoute des règles spécifiques

### Ajouter des commandes
Crée un fichier `.md` dans `.claude/commands/` :
```bash
# Exemple : créer /deploy
nano /home/Mon_ps/.claude/commands/deploy.md
```

---

## 🐛 Dépannage

### Claude ne lit pas CLAUDE.md
```bash
# Vérifie que le fichier existe
cat /home/Mon_ps/CLAUDE.md

# Vérifie les permissions
chmod 644 /home/Mon_ps/CLAUDE.md
```

### Les commandes /continue etc. ne marchent pas
```bash
# Vérifie la structure
ls -la /home/Mon_ps/.claude/commands/

# Les fichiers doivent être en .md
```

### Context à 0% trop vite
- Réduis la taille de CLAUDE.md (garde le minimum)
- Utilise `@docs/fichier.md` pour charger à la demande
- Désactive les MCP servers inutilisés

---

## 📊 Fichiers inclus

| Fichier | Rôle |
|---------|------|
| `CLAUDE.md` | Instructions lues à CHAQUE session |
| `docs/CURRENT_TASK.md` | Suivi de la tâche en cours |
| `docs/DECISIONS.md` | Historique des décisions |
| `docs/CHANGELOG.md` | Log des modifications |
| `.claude/commands/continue.md` | Commande /continue |
| `.claude/commands/save.md` | Commande /save |
| `.claude/commands/status.md` | Commande /status |

---

## 🎯 Résultat attendu

Avec cette configuration :
- ✅ Plus de perte de contexte entre sessions
- ✅ Reprise instantanée avec `/continue`
- ✅ Historique complet des décisions
- ✅ Progression toujours documentée
- ✅ Compact sécurisé avec `/save`

**Tu ne referas plus jamais le même travail deux fois !** 🎉
