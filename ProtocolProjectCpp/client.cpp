#include <iostream>
#include <string>
#include "protocol.h"

using namespace std;

bool send(string sendMessage)
{
    return true;
}

int main()
{
    string inputMessage = "";

    cout << "Message to parse : ";
    cin >> inputMessage;
    cout << "Your message is : " << inputMessage << endl;

    //scanf("%s", message);
    //printf("%s", message);
 
    return 0;
}
