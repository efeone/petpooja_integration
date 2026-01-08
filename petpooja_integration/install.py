import click
from petpooja_integration.setup import after_install as setup

def after_install():
	try:
		print("Setting up Petpooja Integration...")
		setup()

		click.secho("Thank you for installing Petpooja Integration!", fg="green")

	except Exception as e:
		BUG_REPORT_URL = "https://github.com/efeone/petpooja_integration/issues/new"
		click.secho(
			"Installation for PW IOI app failed due to an error."
			" Please try re-installing the app or"
			f" report the issue on {BUG_REPORT_URL} if not resolved.",
			fg="bright_red",
		)
		raise e
