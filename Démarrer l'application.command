#!/bin/bash
#  Double-clique sur ce fichier pour démarrer l'application.
#
#  (macOS associe les fichiers .sh à Xcode, mais les fichiers .command
#   s'ouvrent dans le Terminal et s'exécutent. C'est pour ça que ce
#   fichier porte l'extension .command et non .sh.)

cd "$(dirname "$0")" || exit 1

echo "Démarrage de l'application ia-consultations-publiques..."
echo

bash demarrer.sh

code=$?

echo
if [ "$code" -ne 0 ]; then
  echo "Le démarrage s'est arrêté (code $code). Le message ci-dessus explique pourquoi."
fi
echo "Appuie sur Entrée pour fermer cette fenêtre."
read -r _
