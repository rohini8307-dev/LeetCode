char findTheDifference(char* s, char* t) {
    char c;
    for(int i=0;t[i]!='\0';i++){
        int k=0,p=0;
        for(int j=0;t[j]!='\0';j++){
            if(t[i]==t[j])
                k++;
        }
        for(int l=0;s[l]!='\0';l++){
            if(t[i]==s[l])
            p++;
        }
        if(p!=k) c=t[i];    
    }
    return c;
}
