Gemini API quickstart  |  Google AI for Developers      [Skip to main content](#main-content)

 [![Google AI for Developers](https://www.gstatic.com/devrel-devsite/prod/va786e79970aec04a12496606282a334acd24e2232e80173e6a239f5c02ccbb7e/googledevai/images/lockup-new.svg)](/)

/

*   English
*   Deutsch
*   Español – América Latina
*   Français
*   Indonesia
*   Italiano
*   Polski
*   Português – Brasil
*   Shqip
*   Tiếng Việt
*   Türkçe
*   Русский
*   עברית
*   العربيّة
*   فارسی
*   हिंदी
*   বাংলা
*   ภาษาไทย
*   中文 – 简体
*   中文 – 繁體
*   日本語
*   한국어

Sign in

Veo 3 is now available in the Gemini API! [Learn more](https://developers.googleblog.com/en/veo-3-now-available-gemini-api/)

*   [Home](https://ai.google.dev/)
*   [Gemini API](https://ai.google.dev/gemini-api)
*   [Models](https://ai.google.dev/gemini-api/docs)

Send feedback

Gemini API quickstart


=======================

This quickstart shows you how to install our [libraries](/gemini-api/docs/libraries) and make your first Gemini API request.

Before you begin
----------------

You need a Gemini API key. If you don't already have one, you can [get it for free in Google AI Studio](https://aistudio.google.com/app/apikey).

Install the Google GenAI SDK
----------------------------

### Python

Using [Python 3.9+](https://www.python.org/downloads/), install the [`google-genai` package](https://pypi.org/project/google-genai/) using the following [pip command](https://packaging.python.org/en/latest/tutorials/installing-packages/):

pip install -q -U google-genai

### JavaScript

Using [Node.js v18+](https://nodejs.org/en/download/package-manager), install the [Google Gen AI SDK for TypeScript and JavaScript](https://www.npmjs.com/package/@google/genai) using the following [npm command](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm):

npm install @google/genai

### Go

Install [google.golang.org/genai](https://pkg.go.dev/google.golang.org/genai) in your module directory using the [go get command](https://go.dev/doc/code):

go get google.golang.org/genai

### Java

If you're using Maven, you can install [google-genai](https://github.com/googleapis/java-genai) by adding the following to your dependencies:

<dependencies>
      <dependency>
        <groupId>com.google.genai</groupId>
        <artifactId>google-genai</artifactId>
        <version>1.0.0</version>
      </dependency>
    </dependencies>

### Apps Script

1.  To create a new Apps Script project, go to [script.new](https://script.google.com/u/0/home/projects/create).
2.  Click **Untitled project**.
3.  Rename the Apps Script project **AI Studio** and click **Rename**.
4.  Set your [API key](https://developers.google.com/apps-script/guides/properties#manage_script_properties_manually)
    1.  At the left, click **Project Settings** ![The icon for project settings](https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/settings/default/24px.svg).
    2.  Under **Script Properties** click **Add script property**.
    3.  For **Property**, enter the key name: `GEMINI_API_KEY`.
    4.  For **Value**, enter the value for the API key.
    5.  Click **Save script properties**.
5.  Replace the `Code.gs` file contents with the following code:

Make your first request
-----------------------

Here is an example that uses the [`generateContent`](/api/generate-content#method:-models.generatecontent) method to send a request to the Gemini API using the Gemini 2.5 Flash model.

If you [set your API key](/gemini-api/docs/api-key#set-api-env-var) as the environment variable `GEMINI_API_KEY`, it will be picked up automatically by the client when using the [Gemini API libraries](/gemini-api/docs/libraries). Otherwise you will need to [pass your API key](/gemini-api/docs/api-key#provide-api-key-explicitly) as an argument when initializing the client.

Note that all code samples in the Gemini API docs assume that you have set the environment variable `GEMINI_API_KEY`.

### Python

from google import genai
    
    # The client gets the API key from the environment variable `GEMINI_API_KEY`.
    client = genai.Client()
    
    response = client.models.generate_content(
        model="gemini-2.5-flash", contents="Explain how AI works in a few words"
    )
    print(response.text)

### JavaScript

import { GoogleGenAI } from "@google/genai";
    
    // The client gets the API key from the environment variable `GEMINI_API_KEY`.
    const ai = new GoogleGenAI({});
    
    async function main() {
      const response = await ai.models.generateContent({
        model: "gemini-2.5-flash",
        contents: "Explain how AI works in a few words",
      });
      console.log(response.text);
    }
    
    main();

### Go

package main
    
    import (
        "context"
        "fmt"
        "log"
        "google.golang.org/genai"
    )
    
    func main() {
        ctx := context.Background()
        // The client gets the API key from the environment variable `GEMINI_API_KEY`.
        client, err := genai.NewClient(ctx, nil)
        if err != nil {
            log.Fatal(err)
        }
    
        result, err := client.Models.GenerateContent(
            ctx,
            "gemini-2.5-flash",
            genai.Text("Explain how AI works in a few words"),
            nil,
        )
        if err != nil {
            log.Fatal(err)
        }
        fmt.Println(result.Text())
    }

### Java

package com.example;
    
    import com.google.genai.Client;
    import com.google.genai.types.GenerateContentResponse;
    
    public class GenerateTextFromTextInput {
      public static void main(String[] args) {
        // The client gets the API key from the environment variable `GEMINI_API_KEY`.
        Client client = new Client();
    
        GenerateContentResponse response =
            client.models.generateContent(
                "gemini-2.5-flash",
                "Explain how AI works in a few words",
                null);
    
        System.out.println(response.text());
      }
    }

### Apps Script

// See https://developers.google.com/apps-script/guides/properties
    // for instructions on how to set the API key.
    const apiKey = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');
    function main() {
      const payload = {
        contents: [
          {
            parts: [
              { text: 'Explain how AI works in a few words' },
            ],
          },
        ],
      };
    
      const url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent';
      const options = {
        method: 'POST',
        contentType: 'application/json',
        headers: {
          'x-goog-api-key': apiKey,
        },
        payload: JSON.stringify(payload)
      };
    
      const response = UrlFetchApp.fetch(url, options);
      const data = JSON.parse(response);
      const content = data['candidates'][0]['content']['parts'][0]['text'];
      console.log(content);
    }

### REST

curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent" \
      -H "x-goog-api-key: $GEMINI_API_KEY" \
      -H 'Content-Type: application/json' \
      -X POST \
      -d '{
        "contents": [
          {
            "parts": [
              {
                "text": "Explain how AI works in a few words"
              }
            ]
          }
        ]
      }'

"Thinking" is on by default on many of our code samples
-------------------------------------------------------

Many code samples on this site use the [Gemini 2.5 Flash](/gemini-api/docs/models#gemini-2.5-flash) model, which has the ["thinking"](/gemini-api/docs/thinking) feature enabled by default to enhance response quality. You should be aware that this may increase response time and token usage. If you prioritize speed or wish to minimize costs, you can disable this feature by setting the thinking budget to zero, as shown in the examples below. For more details, see the [thinking guide](/gemini-api/docs/thinking#set-budget).

**Note:** Thinking is only available on Gemini 2.5 series models and can't be disabled on Gemini 2.5 Pro.

### Python

from google import genai
    from google.genai import types
    
    client = genai.Client()
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="Explain how AI works in a few words",
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=0) # Disables thinking
        ),
    )
    print(response.text)

### JavaScript

import { GoogleGenAI } from "@google/genai";
    
    const ai = new GoogleGenAI({});
    
    async function main() {
      const response = await ai.models.generateContent({
        model: "gemini-2.5-flash",
        contents: "Explain how AI works in a few words",
        config: {
          thinkingConfig: {
            thinkingBudget: 0, // Disables thinking
          },
        }
      });
      console.log(response.text);
    }
    
    await main();

### Go

package main
    
    import (
      "context"
      "fmt"
      "os"
      "google.golang.org/genai"
    )
    
    func main() {
    
      ctx := context.Background()
      client, err := genai.NewClient(ctx, nil)
      if err != nil {
          log.Fatal(err)
      }
    
      result, _ := client.Models.GenerateContent(
          ctx,
          "gemini-2.5-flash",
          genai.Text("Explain how AI works in a few words"),
          &genai.GenerateContentConfig{
            ThinkingConfig: &genai.ThinkingConfig{
                ThinkingBudget: int32(0), // Disables thinking
            },
          }
      )
    
      fmt.Println(result.Text())
    }

### REST

curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent" \
      -H "x-goog-api-key: $GEMINI_API_KEY" \
      -H 'Content-Type: application/json' \
      -X POST \
      -d '{
        "contents": [
          {
            "parts": [
              {
                "text": "Explain how AI works in a few words"
              }
            ]
          }
        ]
        "generationConfig": {
          "thinkingConfig": {
            "thinkingBudget": 0
          }
        }
      }'

### Apps Script

// See https://developers.google.com/apps-script/guides/properties
    // for instructions on how to set the API key.
    const apiKey = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');
    
    function main() {
      const payload = {
        contents: [
          {
            parts: [
              { text: 'Explain how AI works in a few words' },
            ],
          },
        ],
      };
    
      const url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent';
      const options = {
        method: 'POST',
        contentType: 'application/json',
        headers: {
          'x-goog-api-key': apiKey,
        },
        payload: JSON.stringify(payload)
      };
    
      const response = UrlFetchApp.fetch(url, options);
      const data = JSON.parse(response);
      const content = data['candidates'][0]['content']['parts'][0]['text'];
      console.log(content);
    }

What's next
-----------

Now that you made your first API request, you might want to explore the following guides that show Gemini in action:

*   [Thinking](/gemini-api/docs/thinking)
*   [Text generation](/gemini-api/docs/text-generation)
*   [Vision](/gemini-api/docs/vision)
*   [Long context](/gemini-api/docs/long-context)
*   [Embeddings](/gemini-api/docs/embeddings)

Send feedback

Except as otherwise noted, the content of this page is licensed under the [Creative Commons Attribution 4.0 License](https://creativecommons.org/licenses/by/4.0/), and code samples are licensed under the [Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0). For details, see the [Google Developers Site Policies](https://developers.google.com/site-policies). Java is a registered trademark of Oracle and/or its affiliates.

Last updated 2025-07-14 UTC.
