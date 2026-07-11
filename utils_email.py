import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit as st

def send_reset_code(to_email, code):
    """
    Envoie un code de réinitialisation par e-mail en utilisant les identifiants
    SMTP configurés dans les secrets Streamlit.
    """
    try:
        if "email" not in st.secrets:
            return False, "Configuration e-mail absente dans secrets.toml. Veuillez configurer [email]."

        smtp_server = st.secrets["email"].get("smtp_server", "smtp.gmail.com")
        smtp_port = st.secrets["email"].get("smtp_port", 587)
        sender_email = st.secrets["email"].get("sender_email")
        sender_password = st.secrets["email"].get("sender_password")

        if not sender_email or not sender_password:
            return False, "Identifiants d'envoi e-mail non configurés."

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = "DarPharm - Réinitialisation de mot de passe"

        body = f"""
        Bonjour,

        Vous avez demandé la réinitialisation de votre mot de passe pour l'application DarPharm.
        Voici votre code de vérification à 6 chiffres :

        {code}

        Si vous n'êtes pas à l'origine de cette demande, veuillez ignorer cet e-mail.

        Cordialement,
        L'équipe DarPharm
        """
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()

        return True, "E-mail envoyé avec succès"
    except Exception as e:
        return False, f"Erreur lors de l'envoi de l'e-mail: {str(e)}"
