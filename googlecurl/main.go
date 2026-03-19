package main

import (
	"bytes"
	"encoding/base64"
	"fmt"
	"io/ioutil"
	"net/http"
	"net/url"
	"os"
	"strings"

	"github.com/CUCyber/ja3transport"
	"github.com/alecthomas/kong"
)

// Captured from Wireshark when performing successful login via
// Raccoon desktop app and extracted from pcap using pyja3
//
// MD5 is dff8a0aa1c904aaea76c5bf624e88333
const googleJA3 = "769,47-53-5-10-49161-49162-49171-49172-50-56-19-4,0-10-11,23-24-25,0"

var args struct {
	URL        string   `arg:"" help:"Fully qualified URL to contact"`
	Method     string   `short:"X" name:"method" help:"HTTP method to use" default:"GET"`
	Headers    []string `sep:"none" short:"H" name:"header" help:"Additional http headers in format 'Header: Value'"`
	Body       string   `name:"body" help:"Request body, must be UTF-8 due to limitation in argument parser"`
	BodyBase64 bool     `name:"body-base64" help:"Assume request body is base64 encoded, so null bytes can be used"`
}

func mainE() error {
	kong.Parse(&args)
	parsedURL, err := url.Parse(args.URL)
	if err != nil {
		return err
	}
	parsedHeaders := http.Header{}
	for _, header := range args.Headers {
		splits := strings.SplitN(header, ": ", 2)
		if len(splits) != 2 {
			return fmt.Errorf("bad header format: %v", header)
		}
		key := splits[0]
		value := splits[1]
		parsedHeaders.Add(key, value)
	}
	if err != nil {
		return err
	}
	parsedBody := []byte(args.Body)
	if args.BodyBase64 {
		encoder := base64.NewDecoder(base64.StdEncoding, bytes.NewReader(parsedBody))
		parsedBody, err = ioutil.ReadAll(encoder)
		if err != nil {
			return err
		}
	}
	req := http.Request{
		Method: args.Method,
		URL:    parsedURL,
		Header: parsedHeaders,
		Body:   ioutil.NopCloser(bytes.NewReader(parsedBody)),
	}
	client, err := ja3transport.NewWithString(googleJA3)
	if err != nil {
		return err
	}
	resp, err := client.Do(&req)
	if err != nil {
		return err
	}
	fmt.Fprintf(os.Stderr, "status %s\n", resp.Status)
	for key, vals := range resp.Header {
		for _, val := range vals {
			fmt.Fprintf(os.Stderr, "header %s: %s\n", key, val)
		}
	}
	respBody, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return err
	}
	fmt.Fprintf(os.Stderr, "body %d bytes\n", len(respBody))
	fmt.Printf("%s", respBody)
	return nil
}

func main() {
	err := mainE()
	if err != nil {
		fmt.Fprintf(os.Stderr, "fatal: %s\n", err.Error())
		os.Exit(1)
	}
}
