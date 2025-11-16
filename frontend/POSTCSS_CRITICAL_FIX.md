# 🚨 CORRECTION CRITIQUE : postcss.config.js

## Date : 16 Novembre 2025

## Problème rencontré
Les classes Tailwind CSS n'étaient **PAS compilées**. Le fichier CSS final contenait :
```
@tailwind base;@tailwind components;@tailwind utilities;
```
Au lieu des vraies classes CSS comme `.rounded-xl`, `.bg-card`, etc.

**Symptôme visible :** Dashboard sans style, texte brut, pas de cards

## Cause racine
**FICHIER MANQUANT : `postcss.config.js`**

Sans ce fichier, Next.js ne sait pas qu'il doit utiliser PostCSS pour transformer les directives Tailwind en CSS réel.

## Solution appliquée
Création du fichier `postcss.config.js` :
```javascript
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

## Vérification
- CSS avant fix : 4219 bytes (directives non compilées)
- CSS après fix : 57576 bytes (classes compilées)

## Comment éviter ce problème à l'avenir
1. **TOUJOURS** vérifier que `postcss.config.js` existe à la racine du projet frontend
2. Lors de l'initialisation d'un projet Next.js + Tailwind, s'assurer que PostCSS est configuré
3. Si le CSS ne s'applique pas, vérifier en premier :
   - `postcss.config.js` existe
   - `tailwind.config.ts` a les bons chemins dans `content`
   - `globals.css` importe les directives @tailwind

## Commande de diagnostic
```bash
# Vérifier si les classes sont compilées
docker exec monps_frontend cat /app/.next/static/css/*.css | head -100 | grep "@tailwind"
# Si @tailwind apparaît → PostCSS non configuré !
```
