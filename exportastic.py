import argparse
import grab
from os import walk, path
from urllib.parse import urlparse, urljoin


BASE_URL = "https://www.runtastic.com"
SIGN_IN_URL = urljoin(BASE_URL, "/en/d/users/sign_in")
API_URL = urljoin(BASE_URL, "/api/run_sessions/json")


def parse_args():
    parser = argparse.ArgumentParser(description="Runtastic bulk export.")
    parser.add_argument("-u", "--user", required=True, help="user")
    parser.add_argument("-p", "--password", required=True, help="password")
    parser.add_argument("-e", "--extension", default="gpx", help="extension of export files")
    parser.add_argument("-o", "--output", default=".", help="output directory")
    return parser.parse_args()


def login(user, password):
    g = grab.Grab()
    g.setup(
        post={
            "user[email]": user,
            "user[password]": password,
            "grant_type": "password",
            "authenticity_token": "undefined"
        },
       timeout=60000
    )
    g.go(SIGN_IN_URL)
    return g


def get_authenticity_token(g):
    return g.doc.select("//*[@name='csrf-token']").attr("content")


def get_user_id(g):
    return urlparse(g.doc.url).path.split("/")[3]


def get_items(g, user_id):
    sessions_url = urljoin(BASE_URL, "/en/users/{}/sport-sessions".format(user_id))
    g.go(sessions_url)
    indexes_script = g.doc.select("//script[re:test(text(),'var index_data','i')]")
    indexes = eval(indexes_script.text().split(";")[0].split("=")[1].strip())
    return ",".join([str(els[0]) for els in indexes])


def get_sessions(g, authenticity_token, user_id, items):
    g.go(
        API_URL,
        post={
            "authenticity_token": authenticity_token,
            "user_id": user_id,
            "locale": "en",
            "items": items
        }
    )
    return g.doc.json


def is_file_exported(session_id, output_directory):
    (_, _, filenames) = next(walk(output_directory))
    for filename in filenames:
        if str(session_id) in filename:
            return True
    return False


def download_data(g, sessions, extension, output_directory):
    for session in sessions:
        page_url = session["page_url"]
        session_id = session["id"]
        export_url = urljoin(BASE_URL, "{}.{}".format(page_url, extension))
        if not is_file_exported(session_id, output_directory):
            g.go(export_url)
        else:
            continue
        try:
            file_name = "{}_{}".format(
                session_id, g.doc.headers.get("Content-Disposition").split("=")[1].strip('"'))
        except AttributeError:
            print("Captcha solving required. {}".format(urljoin(BASE_URL, page_url)))
            not input("Press enter to continue: ")
        else:
            print(file_name)
            g.doc.save(path.join(output_directory, file_name))


def main():
    args = parse_args()
    g = login(args.user, args.password)
    authenticity_token = get_authenticity_token(g)
    user_id = get_user_id(g)
    items = get_items(g, user_id)
    sessions = get_sessions(g, authenticity_token, user_id, items)
    download_data(g, sessions, args.extension, args.output)


if __name__ == "__main__":
    main()
